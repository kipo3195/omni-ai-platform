from fastapi import FastAPI

from app.api.v1.router import create_api_v1_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.features.conversation_start.composition import (
    create_conversation_start_runner,
)
from app.features.returned_message_topics.composition import (
    create_returned_message_topics_handler,
)
from app.features.trending.composition import create_trending_service
from app.shared.llm.factory import create_llm_client


def create_app() -> FastAPI:
    setup_logging()

    llm_client = create_llm_client(settings)

    trending_service = create_trending_service(
        llm_client=llm_client,
    )

    conversation_start_runner = create_conversation_start_runner(
        trending_context_provider=trending_service,
    )
    returned_message_topics_handler = create_returned_message_topics_handler(
        llm_client=llm_client,
    )

    app = FastAPI(
        title="Omni AI Platform",
    )

    app.include_router(
        create_api_v1_router(
            conversation_start_runner=conversation_start_runner,
            returned_message_topics_handler=returned_message_topics_handler,
            trending_refresher=trending_service,
        )
    )

    @app.get("/health")
    async def health():
        return {
            "status": "ok"
        }

    return app
