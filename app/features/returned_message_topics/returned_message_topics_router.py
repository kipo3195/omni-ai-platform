from fastapi import APIRouter

from app.features.ai_task.ai_task_executor import AiTaskExecutor
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsInput,
    ReturnedMessageTopicsRequest,
    ReturnedMessageTopicsResult,
    ReturnedMessageTopicsSuccessResponse,
)
from app.features.returned_message_topics.returned_message_topics_handler import (
    ReturnedMessageTopicsHandler,
)


router = APIRouter(
    prefix="/returned-message-topics",
    tags=["returned-message-topics"],
)

executor = AiTaskExecutor[ReturnedMessageTopicsInput, ReturnedMessageTopicsResult]()
handler = ReturnedMessageTopicsHandler()


@router.post(
    "/generate",
    response_model=ReturnedMessageTopicsSuccessResponse,
)
async def generate_returned_message_topics(
    request: ReturnedMessageTopicsRequest,
) -> ReturnedMessageTopicsSuccessResponse:
    response = await executor.execute(
        request=request,
        handler=handler,
    )
    return ReturnedMessageTopicsSuccessResponse.model_validate(response.model_dump())
