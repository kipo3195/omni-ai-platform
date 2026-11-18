import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.returned_message_topics.mariadb_execution_repository import (
    RECOVERY_LEASE_EXPIRED,
    RECOVERY_NONE,
    MariaDbReturnedMessageTopicsExecutionRepository,
)
from app.features.returned_message_topics.execution_service import (
    ReturnedMessageTopicsExecutionService,
)
from app.features.returned_message_topics.returned_message_topics_router import (
    create_returned_message_topics_router,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageAssessment,
    ReturnedMessageTopic,
    ReturnedMessageTopicsRequest,
    ReturnedMessageTopicsResult,
)


VALID_REQUEST = {
    "execution_id": "execution-1",
    "tenant_id": "tenant-1",
    "task_type": "RETURNED_MESSAGE_TOPICS",
    "contract_version": 2,
    "input": {
        "request_id": "request-1",
        "user_id": "user-1",
        "absence_period_id": "period-1",
        "message_selection_ref": "selection-1",
        "selected_items": [
            {
                "source_item_key": "MSG_KEY_1",
                "subject": "업무 보고",
                "sequence": 0,
            }
        ],
    },
}
TENANT_HEADERS = {"X-Tenant-Id": "tenant-1"}


class FakeReturnedMessageTopicsHandler:
    def __init__(self):
        self.calls = 0

    async def execute(self, execution_id, tenant_id, task_input):
        self.calls += 1
        return ReturnedMessageTopicsResult(
            topics=[
                ReturnedMessageTopic(
                    topic="업무 보고",
                    summary="업무 보고 관련 쪽지입니다.",
                    source_message_refs=["MSG_KEY_1"],
                )
            ],
            message_assessments=[
                ReturnedMessageAssessment(
                    message_ref="MSG_KEY_1",
                    priority="UNKNOWN",
                    priority_reason="제목만으로 우선순위를 판단하기 어렵습니다.",
                    reply_required=False,
                    reply_reason="명시적인 답변 요청이 없습니다.",
                    action_required=False,
                    action_reason="명시적인 후속 조치 요청이 없습니다.",
                )
            ],
            generated_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )


@pytest.fixture
def repository_factory():
    datasource_url = os.getenv("TEST_DATASOURCE_URL")
    username = os.getenv("TEST_DATASOURCE_USERNAME")
    password = os.getenv("TEST_DATASOURCE_PASSWORD")
    if not datasource_url or not username:
        pytest.skip("MariaDB integration test datasource is not configured")

    table_prefix = f"test_{uuid4().hex[:8]}_"
    repositories = []

    def create_repository():
        repository = MariaDbReturnedMessageTopicsExecutionRepository(
            datasource_url=datasource_url,
            username=username,
            password=password or "",
            table_prefix=table_prefix,
        )
        repositories.append(repository)
        return repository

    yield create_repository

    if repositories:
        repository = repositories[0]
        with repository._connection() as connection, connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {repository._outbox_table}")
            cursor.execute(f"DROP TABLE IF EXISTS {repository._execution_table}")
            connection.commit()


@pytest.fixture
def execution_context(repository_factory):
    handler = FakeReturnedMessageTopicsHandler()
    service = ReturnedMessageTopicsExecutionService(
        repository=repository_factory(),
        handler=handler,
        worker_count=1,
        execution_lease_seconds=1.0,
        recovery_poll_interval_seconds=0.01,
    )
    service.start()
    app = FastAPI()
    app.include_router(
        create_returned_message_topics_router(service),
        prefix="/ai/v1",
    )
    with TestClient(app) as client:
        yield client, handler
    service.close()


def await_terminal(client: TestClient, execution_id: str) -> dict:
    deadline = monotonic() + 2.0
    while monotonic() < deadline:
        response = client.get(
            f"/ai/v1/returned-message-topics/executions/{execution_id}",
            headers={"X-Tenant-Id": "tenant-1"},
        )
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return body
        sleep(0.01)
    raise AssertionError("execution did not reach a terminal state")


def test_generate_returned_message_topics_accepts_and_completes_async(
    execution_context,
):
    client, handler = execution_context
    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
        headers=TENANT_HEADERS,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["execution_id"] == "execution-1"
    assert body["task_type"] == "RETURNED_MESSAGE_TOPICS"
    assert body["contract_version"] == 2
    assert body["status"] == "ACCEPTED"

    body = await_terminal(client, "execution-1")
    assert body["status"] == "SUCCEEDED"
    assert body["result"]["topics"] == [
        {
            "topic": "업무 보고",
            "summary": "업무 보고 관련 쪽지입니다.",
            "source_message_refs": ["MSG_KEY_1"],
        }
    ]
    assert body["result"]["message_assessments"] == [
        {
            "message_ref": "MSG_KEY_1",
            "priority": "UNKNOWN",
            "priority_reason": "제목만으로 우선순위를 판단하기 어렵습니다.",
            "reply_required": False,
            "reply_reason": "명시적인 답변 요청이 없습니다.",
            "action_required": False,
            "action_reason": "명시적인 후속 조치 요청이 없습니다.",
        }
    ]
    assert body["result"]["generated_at"] == "2026-11-02T00:00:00Z"
    assert handler.calls == 1


def test_generate_returned_message_topics_rejects_unknown_task_type(
    execution_context,
):
    request = deepcopy(VALID_REQUEST)
    request["task_type"] = "CONVERSATION_START"
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_rejects_unsupported_contract_version(
    execution_context,
):
    request = deepcopy(VALID_REQUEST)
    request["contract_version"] = 1
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_requires_selected_items(
    execution_context,
):
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"] = []
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_allows_nullable_subject(
    execution_context,
):
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"][0]["subject"] = None
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 202


def test_generate_returned_message_topics_rejects_duplicate_source_keys(
    execution_context,
):
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"].append(
        {
            "source_item_key": "MSG_KEY_1",
            "subject": "중복 쪽지",
            "sequence": 1,
        }
    )
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_rejects_duplicate_sequences(
    execution_context,
):
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"].append(
        {
            "source_item_key": "MSG_KEY_2",
            "subject": "다른 쪽지",
            "sequence": 0,
        }
    )
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 422


def test_duplicate_start_returns_existing_execution_without_rerunning(
    execution_context,
):
    client, handler = execution_context

    assert client.post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
        headers=TENANT_HEADERS,
    ).status_code == 202
    await_terminal(client, "execution-1")

    duplicate = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
        headers=TENANT_HEADERS,
    )

    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "SUCCEEDED"
    assert handler.calls == 1


def test_duplicate_execution_with_different_request_returns_conflict(
    execution_context,
):
    client, _ = execution_context
    assert client.post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
        headers=TENANT_HEADERS,
    ).status_code == 202

    changed = deepcopy(VALID_REQUEST)
    changed["input"]["message_selection_ref"] = "another-selection"
    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=changed,
        headers=TENANT_HEADERS,
    )

    assert response.status_code == 409


def test_status_query_is_tenant_scoped(execution_context):
    client, _ = execution_context
    assert client.post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
        headers=TENANT_HEADERS,
    ).status_code == 202

    response = client.get(
        "/ai/v1/returned-message-topics/executions/execution-1",
        headers={"X-Tenant-Id": "another-tenant"},
    )

    assert response.status_code == 404


def test_generate_rejects_mismatched_tenant_header(execution_context):
    response = execution_context[0].post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
        headers={"X-Tenant-Id": "another-tenant"},
    )

    assert response.status_code == 403


def test_accepted_execution_is_recovered_from_persistent_store(
    repository_factory,
):
    repository = repository_factory()
    request = ReturnedMessageTopicsRequest.model_validate(VALID_REQUEST)
    record, created = repository.accept(request)
    assert created is True
    assert record.status == "ACCEPTED"

    handler = FakeReturnedMessageTopicsHandler()
    service = ReturnedMessageTopicsExecutionService(
        repository=repository_factory(),
        handler=handler,
        worker_count=1,
        execution_lease_seconds=1.0,
        recovery_poll_interval_seconds=0.01,
    )
    service.start()
    try:
        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            execution = service.find("tenant-1", "execution-1")
            if execution is not None and execution.status == "SUCCEEDED":
                break
            sleep(0.01)
        else:
            raise AssertionError("persisted execution was not recovered")
    finally:
        service.close()

    assert handler.calls == 1


def test_expired_running_execution_is_isolated_without_reexecution(
    repository_factory,
):
    repository = repository_factory()
    request = ReturnedMessageTopicsRequest.model_validate(VALID_REQUEST)
    repository.accept(request)
    assert repository.claim_execution(
        "tenant-1",
        "execution-1",
        "worker-1",
        lease_seconds=0.01,
    ) is True
    sleep(0.02)

    handler = FakeReturnedMessageTopicsHandler()
    service = ReturnedMessageTopicsExecutionService(
        repository=repository_factory(),
        handler=handler,
        worker_count=1,
        execution_lease_seconds=1.0,
        recovery_poll_interval_seconds=0.01,
    )
    service.start()
    try:
        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            record = repository.find("tenant-1", "execution-1")
            if record is not None and (
                record.recovery_status == RECOVERY_LEASE_EXPIRED
            ):
                break
            sleep(0.01)
        else:
            raise AssertionError("expired running execution was not isolated")

        sleep(0.05)
        record = repository.find("tenant-1", "execution-1")
        assert record is not None
        assert record.status == "RUNNING"
        assert record.recovery_status == RECOVERY_LEASE_EXPIRED
        assert record.recovery_detected_at is not None
        assert handler.calls == 0
        assert repository.claim_execution(
            "tenant-1",
            "execution-1",
            "worker-2",
            lease_seconds=1.0,
        ) is False
    finally:
        service.close()

    assert repository.complete_failure(
        tenant_id="tenant-1",
        execution_id="execution-1",
        owner="worker-1",
        error_payload={
            "code": "AI_GENERATION_FAILED",
            "message": "generation failed",
            "retryable": False,
        },
        callback_payload={
            "tenantId": "tenant-1",
            "userId": "user-1",
            "executionId": "execution-1",
            "taskType": "RETURNED_MESSAGE_TOPICS",
            "contractVersion": 2,
            "status": "FAILED",
            "failureReason": "AI_GENERATION_FAILED",
        },
    ) is True
    completed = repository.find("tenant-1", "execution-1")
    assert completed is not None
    assert completed.status == "FAILED"
    assert completed.recovery_status == RECOVERY_NONE
    assert completed.recovery_detected_at is None


def test_callback_outbox_retries_same_event_until_accepted(repository_factory):
    deliveries: list[dict] = []

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers["Content-Length"])
            deliveries.append(
                {
                    "path": self.path,
                    "tenant_id": self.headers["X-Tenant-Id"],
                    "body": json.loads(self.rfile.read(content_length)),
                }
            )
            self.send_response(503 if len(deliveries) == 1 else 202)
            self.end_headers()

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), CallbackHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    service = ReturnedMessageTopicsExecutionService(
        repository=repository_factory(),
        handler=FakeReturnedMessageTopicsHandler(),
        worker_count=1,
        execution_lease_seconds=1.0,
        recovery_poll_interval_seconds=0.01,
        callback_base_url=f"http://127.0.0.1:{server.server_port}",
        callback_timeout_seconds=0.5,
        callback_poll_interval_seconds=0.01,
        callback_retry_initial_seconds=0.01,
        callback_retry_max_seconds=0.02,
    )
    service.start()
    try:
        service.accept(ReturnedMessageTopicsRequest.model_validate(VALID_REQUEST))
        deadline = monotonic() + 2.0
        while monotonic() < deadline and len(deliveries) < 2:
            sleep(0.01)
        assert len(deliveries) == 2
    finally:
        service.close()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1.0)

    first, second = deliveries
    assert first["path"] == (
        "/api/v1/returned-messages/request-1/execution-results"
    )
    assert first["tenant_id"] == "tenant-1"
    assert first["body"]["eventId"] == second["body"]["eventId"]
    assert first["body"]["executionId"] == "execution-1"
    assert first["body"]["taskType"] == "RETURNED_MESSAGE_TOPICS"
    assert first["body"]["contractVersion"] == 2
    assert first["body"]["status"] == "SUCCEEDED"
    assert first["body"]["result"]["messageAssessments"][0][
        "messageRef"
    ] == "MSG_KEY_1"


def test_callback_outbox_moves_to_dead_letter_after_retry_budget(
    repository_factory,
):
    repository = repository_factory()
    request = ReturnedMessageTopicsRequest.model_validate(VALID_REQUEST)
    repository.accept(request)
    repository.claim_execution(
        "tenant-1",
        "execution-1",
        "worker-1",
        lease_seconds=1.0,
    )
    repository.complete_failure(
        tenant_id="tenant-1",
        execution_id="execution-1",
        owner="worker-1",
        error_payload={
            "code": "AI_GENERATION_FAILED",
            "message": "generation failed",
            "retryable": False,
        },
        callback_payload={
            "tenantId": "tenant-1",
            "userId": "user-1",
            "executionId": "execution-1",
            "taskType": "RETURNED_MESSAGE_TOPICS",
            "contractVersion": 2,
            "status": "FAILED",
            "failureReason": "AI_GENERATION_FAILED",
        },
    )
    event = repository.claim_due_outbox("worker-1", lease_seconds=1.0)
    assert event is not None

    repository.reschedule_outbox(
        event.event_id,
        "worker-1",
        delay_seconds=0.0,
        last_error="HTTP_422",
        max_attempts=1,
    )

    assert repository.claim_due_outbox(
        "worker-2",
        lease_seconds=1.0,
    ) is None


def test_execution_lease_allows_only_one_worker_owner(repository_factory):
    repository = repository_factory()
    request = ReturnedMessageTopicsRequest.model_validate(VALID_REQUEST)
    repository.accept(request)

    assert repository.claim_execution(
        "tenant-1",
        "execution-1",
        "worker-1",
        lease_seconds=10.0,
    ) is True
    assert repository.claim_execution(
        "tenant-1",
        "execution-1",
        "worker-2",
        lease_seconds=10.0,
    ) is False
