# FastAPI 진입점
from fastapi import APIRouter

from app.features.conversation_start.ports import ConversationStartRunner
from app.features.conversation_start.conversation_start_schemas import (
    ConversationStartRequest,
    ConversationStartResponse,
)
from app.features.conversation_start.conversation_start_state import (
    ConversationStartState,
)


def create_conversation_start_router(
    runner: ConversationStartRunner,
) -> APIRouter:
    router = APIRouter(
        prefix="/chat/suggestions",
        tags=["conversation-start"],
    )

    @router.post(
        "/generate",
        response_model=ConversationStartResponse,
    )
    async def chat_suggest(
        request: ConversationStartRequest,
    ) -> ConversationStartResponse:

        initial_state: ConversationStartState = {
            "session_id": request.session_id,
            "user_id": request.user_id,
            "room_id": request.room_id,
            "messages": request.messages,
            "suggestion_type": request.suggestion_type,
            "options": request.options,
        }

        result = await runner.ainvoke(initial_state)

        return ConversationStartResponse(
            session_id=request.session_id,
            suggestions=result.get(
                "selected_messages",
                [],
            ),
        )

    return router
