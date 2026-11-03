from typing import TypedDict

from app.features.conversation_start.conversation_start_schemas import (
    ChatMessage,
    ConversationStartSuggestion,
    RequestOptions,
    SuggestionType,
)
from app.features.trending.trending_models import EvaluatedTrendingTopic


class ConversationStartState(TypedDict, total=False):
    session_id: str
    user_id: str
    room_id: str

    suggestion_type: SuggestionType
    messages: list[ChatMessage]
    options: RequestOptions

    analyzed_context: dict
    trending_context: list[EvaluatedTrendingTopic]

    candidate_messages: list[ConversationStartSuggestion]
    selected_messages: list[ConversationStartSuggestion]
