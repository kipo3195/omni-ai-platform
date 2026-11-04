from time import monotonic

from fastapi import APIRouter

from app.features.ai_task.ai_task_executor import AiTaskExecutor
from app.features.ai_task.ai_task_handler import AiTaskHandler
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsInput,
    ReturnedMessageTopicsRequest,
    ReturnedMessageTopicsResult,
    ReturnedMessageTopicsSuccessResponse,
)
from app.features.returned_message_topics.trace import (
    trace_development,
    trace_exception,
    trace_info,
)


def create_returned_message_topics_router(
    handler: AiTaskHandler[ReturnedMessageTopicsInput, ReturnedMessageTopicsResult],
) -> APIRouter:
    router = APIRouter(
        prefix="/returned-message-topics",
        tags=["returned-message-topics"],
    )
    # 공통 실행기 AiTaskExecutor의 인스턴스를 생성, 처리할 타입을 지정
    executor = AiTaskExecutor[ReturnedMessageTopicsInput, ReturnedMessageTopicsResult]()

    @router.post(
        "/generate",
        response_model=ReturnedMessageTopicsSuccessResponse,
    )
    async def generate_returned_message_topics(
        request: ReturnedMessageTopicsRequest,
    ) -> ReturnedMessageTopicsSuccessResponse:
        started_at = monotonic()
        trace_info(
            "request_received",
            execution_id=request.execution_id,
            request_id=request.input.request_id,
            selected_item_count=len(request.input.selected_items),
            tenant_id=request.tenant_id,
        )

        # HTTP 요청이 들어왔을 때
        try:
            response = await executor.execute(
                request=request,
                handler=handler,
            )
            success_response = ReturnedMessageTopicsSuccessResponse.model_validate(
                response.model_dump()
            )
        except Exception as exc:
            trace_exception(
                "request_failed",
                elapsed_ms=int((monotonic() - started_at) * 1000),
                error_type=type(exc).__name__,
                execution_id=request.execution_id,
                request_id=request.input.request_id,
            )
            raise

        trace_info(
            "request_completed",
            elapsed_ms=int((monotonic() - started_at) * 1000),
            execution_id=request.execution_id,
            request_id=request.input.request_id,
            topic_count=len(success_response.result.topics),
        )
        trace_development(
            "http_response_payload",
            execution_id=request.execution_id,
            request_id=request.input.request_id,
            response=success_response.model_dump(mode="json"),
        )
        return success_response

    return router
