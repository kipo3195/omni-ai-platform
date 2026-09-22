from typing import TypedDict
from app.features.trending.trending_models import TrendingTopic

from app.features.conversation_start.conversation_start_schemas import (
        ChatMessage,
        ConversationStartSuggestion,
        RequestOptions,
        SuggestionType,
    )


class ConversationStartState(TypedDict, total=False):
    session_id: str
    user_id: str
    room_id: str

    suggestion_type: SuggestionType
    messages: list[ChatMessage]
    options: RequestOptions

    analyzed_context: dict
    trending_context: list[TrendingTopic]

    candidate_messages: list[ConversationStartSuggestion]
    selected_messages: list[ConversationStartSuggestion]
