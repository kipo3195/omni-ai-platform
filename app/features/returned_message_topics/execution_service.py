import asyncio
import json
import logging
import queue
import threading
import uuid
from urllib.parse import quote

import httpx

from app.features.ai_task.ai_task_handler import AiTaskHandler
from app.features.ai_task.ai_task_schemas import AiTaskError
from app.features.returned_message_topics.mariadb_execution_repository import (
    CONTRACT_VERSION,
    TASK_TYPE,
    ExecutionRecord,
    MariaDbReturnedMessageTopicsExecutionRepository,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsAcceptedResponse,
    ReturnedMessageTopicsCancelledResponse,
    ReturnedMessageTopicsExecutionResponse,
    ReturnedMessageTopicsFailureResponse,
    ReturnedMessageTopicsInput,
    ReturnedMessageTopicsRequest,
    ReturnedMessageTopicsResult,
    ReturnedMessageTopicsRunningResponse,
    ReturnedMessageTopicsSuccessResponse,
)


logger = logging.getLogger(__name__)


class ReturnedMessageTopicsExecutionService:
    def __init__(
        self,
        *,
        repository: MariaDbReturnedMessageTopicsExecutionRepository,
        handler: AiTaskHandler[
            ReturnedMessageTopicsInput,
            ReturnedMessageTopicsResult,
        ],
        worker_count: int = 2,
        execution_lease_seconds: float = 300.0,
        recovery_poll_interval_seconds: float = 5.0,
        callback_base_url: str = "",
        callback_timeout_seconds: float = 5.0,
        callback_poll_interval_seconds: float = 1.0,
        callback_retry_initial_seconds: float = 5.0,
        callback_retry_max_seconds: float = 300.0,
        callback_max_attempts: int = 10,
    ):
        if worker_count < 1:
            raise ValueError("worker_count must be positive")
        if execution_lease_seconds <= 0:
            raise ValueError("execution_lease_seconds must be positive")
        if recovery_poll_interval_seconds <= 0:
            raise ValueError("recovery_poll_interval_seconds must be positive")
        if callback_max_attempts < 1:
            raise ValueError("callback_max_attempts must be positive")
        self._repository = repository
        self._handler = handler
        self._worker_count = worker_count
        self._execution_lease_seconds = execution_lease_seconds
        self._recovery_poll_interval_seconds = recovery_poll_interval_seconds
        self._callback_base_url = callback_base_url.rstrip("/")
        self._callback_timeout_seconds = callback_timeout_seconds
        self._callback_poll_interval_seconds = callback_poll_interval_seconds
        self._callback_retry_initial_seconds = callback_retry_initial_seconds
        self._callback_retry_max_seconds = callback_retry_max_seconds
        self._callback_max_attempts = callback_max_attempts
        self._execution_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._queued: set[tuple[str, str]] = set()
        self._queued_lock = threading.Lock()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for index in range(self._worker_count):
            thread = threading.Thread(
                target=self._execution_worker,
                name=f"rmt-execution-{index + 1}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

        recovery_thread = threading.Thread(
            target=self._recovery_worker,
            name="rmt-recovery-1",
            daemon=True,
        )
        recovery_thread.start()
        self._threads.append(recovery_thread)

        if self._callback_base_url:
            callback_thread = threading.Thread(
                target=self._callback_worker,
                name="rmt-callback-1",
                daemon=True,
            )
            callback_thread.start()
            self._threads.append(callback_thread)

    def close(self) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=2.0)

    def accept(
        self,
        request: ReturnedMessageTopicsRequest,
    ) -> ReturnedMessageTopicsExecutionResponse:
        if not self._started:
            self.start()
        record, created = self._repository.accept(request)
        if created or record.status == "ACCEPTED":
            self._enqueue(record.tenant_id, record.execution_id)
        return self._to_response(record)

    def find(
        self,
        tenant_id: str,
        execution_id: str,
    ) -> ReturnedMessageTopicsExecutionResponse | None:
        record = self._repository.find(tenant_id, execution_id)
        return None if record is None else self._to_response(record)

    def _enqueue(self, tenant_id: str, execution_id: str) -> None:
        key = (tenant_id, execution_id)
        with self._queued_lock:
            if key in self._queued:
                return
            self._queued.add(key)
        self._execution_queue.put(key)

    def _execution_worker(self) -> None:
        owner = str(uuid.uuid4())
        while not self._stop.is_set():
            try:
                tenant_id, execution_id = self._execution_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self._execute(tenant_id, execution_id, owner)
            except Exception:
                logger.exception(
                    "Returned Message Topics worker failed unexpectedly. "
                    "execution_id=%s",
                    execution_id,
                )
            finally:
                with self._queued_lock:
                    self._queued.discard((tenant_id, execution_id))
                self._execution_queue.task_done()

    def _recovery_worker(self) -> None:
        while not self._stop.is_set():
            try:
                marked = self._repository.mark_expired_running()
                if marked:
                    logger.warning(
                        "Marked expired Returned Message Topics executions "
                        "for recovery isolation. count=%s",
                        marked,
                    )
                for tenant_id, execution_id in (
                    self._repository.find_accepted_for_recovery()
                ):
                    self._enqueue(tenant_id, execution_id)
            except Exception:
                logger.exception(
                    "Returned Message Topics recovery scan failed"
                )
            self._stop.wait(self._recovery_poll_interval_seconds)

    def _execute(
        self,
        tenant_id: str,
        execution_id: str,
        owner: str,
    ) -> None:
        record = self._repository.find(tenant_id, execution_id)
        if record is None or record.status != "ACCEPTED":
            return
        if not self._repository.claim_execution(
            tenant_id,
            execution_id,
            owner,
            self._execution_lease_seconds,
        ):
            return

        request = ReturnedMessageTopicsRequest.model_validate_json(
            record.request_payload
        )
        try:
            result = asyncio.run(
                self._handler.execute(
                    execution_id=request.execution_id,
                    tenant_id=request.tenant_id,
                    task_input=request.input,
                )
            )
            validated = ReturnedMessageTopicsResult.model_validate(result)
            result_payload = validated.model_dump(mode="json")
            self._repository.complete_success(
                tenant_id=tenant_id,
                execution_id=execution_id,
                owner=owner,
                result_payload=result_payload,
                callback_payload=_success_callback(request, validated),
            )
        except Exception as exception:
            logger.exception(
                "Returned Message Topics execution failed. execution_id=%s",
                execution_id,
            )
            error = {
                "code": "AI_GENERATION_FAILED",
                "message": "Returned Message Topics generation failed",
                "retryable": False,
            }
            self._repository.complete_failure(
                tenant_id=tenant_id,
                execution_id=execution_id,
                owner=owner,
                error_payload=error,
                callback_payload=_failure_callback(request, error),
            )

    def _callback_worker(self) -> None:
        owner = str(uuid.uuid4())
        with httpx.Client(timeout=self._callback_timeout_seconds) as client:
            while not self._stop.is_set():
                event = self._repository.claim_due_outbox(
                    owner,
                    lease_seconds=max(self._callback_timeout_seconds * 2, 10.0),
                )
                if event is None:
                    self._stop.wait(self._callback_poll_interval_seconds)
                    continue

                url = (
                    f"{self._callback_base_url}/api/v1/returned-messages/"
                    f"{quote(event.request_id, safe='')}/execution-results"
                )
                try:
                    response = client.post(
                        url,
                        json=json.loads(event.payload),
                        headers={"X-Tenant-Id": event.tenant_id},
                    )
                    if 200 <= response.status_code < 300:
                        self._repository.mark_outbox_delivered(
                            event.event_id,
                            owner,
                        )
                        continue
                    error = f"HTTP_{response.status_code}"
                except httpx.HTTPError as exception:
                    error = type(exception).__name__

                delay = min(
                    self._callback_retry_max_seconds,
                    self._callback_retry_initial_seconds
                    * (2 ** min(event.attempt_count, 8)),
                )
                self._repository.reschedule_outbox(
                    event.event_id,
                    owner,
                    delay_seconds=delay,
                    last_error=error,
                    max_attempts=self._callback_max_attempts,
                )

    def _to_response(
        self,
        record: ExecutionRecord,
    ) -> ReturnedMessageTopicsExecutionResponse:
        common = {
            "execution_id": record.execution_id,
            "task_type": TASK_TYPE,
            "contract_version": CONTRACT_VERSION,
        }
        if record.status == "ACCEPTED":
            return ReturnedMessageTopicsAcceptedResponse(**common)
        if record.status == "RUNNING":
            return ReturnedMessageTopicsRunningResponse(**common)
        if record.status == "SUCCEEDED":
            if record.result_payload is None:
                raise RuntimeError("succeeded execution does not contain a result")
            return ReturnedMessageTopicsSuccessResponse(
                **common,
                result=ReturnedMessageTopicsResult.model_validate_json(
                    record.result_payload
                ),
            )
        if record.status == "FAILED":
            if record.error_payload is None:
                raise RuntimeError("failed execution does not contain an error")
            return ReturnedMessageTopicsFailureResponse(
                **common,
                error=AiTaskError.model_validate_json(record.error_payload),
            )
        if record.status == "CANCELLED":
            return ReturnedMessageTopicsCancelledResponse(**common)
        raise RuntimeError(f"Unsupported execution status: {record.status}")


def _success_callback(
    request: ReturnedMessageTopicsRequest,
    result: ReturnedMessageTopicsResult,
) -> dict[str, object]:
    return {
        "tenantId": request.tenant_id,
        "userId": request.input.user_id,
        "executionId": request.execution_id,
        "taskType": TASK_TYPE,
        "contractVersion": CONTRACT_VERSION,
        "status": "SUCCEEDED",
        "result": {
            "topics": [
                {
                    "topic": topic.topic,
                    "summary": topic.summary,
                    "sourceMessageRefs": topic.source_message_refs,
                }
                for topic in result.topics
            ],
            "messageAssessments": [
                {
                    "messageRef": assessment.message_ref,
                    "priority": assessment.priority.value,
                    "priorityReason": assessment.priority_reason,
                    "replyRequired": assessment.reply_required,
                    "replyReason": assessment.reply_reason,
                    "actionRequired": assessment.action_required,
                    "actionReason": assessment.action_reason,
                }
                for assessment in result.message_assessments
            ],
            "generatedAt": result.generated_at.isoformat().replace(
                "+00:00",
                "Z",
            ),
        },
    }


def _failure_callback(
    request: ReturnedMessageTopicsRequest,
    error: dict[str, object],
) -> dict[str, object]:
    return {
        "tenantId": request.tenant_id,
        "userId": request.input.user_id,
        "executionId": request.execution_id,
        "taskType": TASK_TYPE,
        "contractVersion": CONTRACT_VERSION,
        "status": "FAILED",
        "failureReason": error["code"],
    }
