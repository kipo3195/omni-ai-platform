from fastapi import APIRouter

from app.features.conversation_start.conversation_start_router import (
    create_conversation_start_router,
)
from app.features.conversation_start.ports import ConversationStartRunner
from app.features.returned_message_topics.returned_message_topics_router import (
    create_returned_message_topics_router,
)
from app.features.ai_task.ai_task_handler import AiTaskHandler
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsInput,
    ReturnedMessageTopicsResult,
)
from app.features.trending.ports import TrendingRefresher
from app.features.trending.trending_router import create_trending_router


def create_api_v1_router(
    *,
    conversation_start_runner: ConversationStartRunner,
    returned_message_topics_handler: AiTaskHandler[
        ReturnedMessageTopicsInput,
        ReturnedMessageTopicsResult,
    ],
    trending_refresher: TrendingRefresher,
) -> APIRouter:
    router = APIRouter(prefix="/ai/v1")

    router.include_router(
        create_conversation_start_router(conversation_start_runner)
    )
    router.include_router(
        create_returned_message_topics_router(returned_message_topics_handler)
    )
    router.include_router(
        create_trending_router(trending_refresher)
    )

    return router
