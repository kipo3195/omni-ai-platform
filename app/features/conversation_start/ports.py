from typing import Protocol

from app.features.conversation_start.conversation_start_state import (
    ConversationStartState,
)
from app.features.trending.trending_models import EvaluatedTrendingTopic


class TrendingContextProvider(Protocol):
    async def get_context(
        self,
        limit: int = 10,
        exclude_topics: list[str] | None = None,
    ) -> list[EvaluatedTrendingTopic]:
        ...


class ConversationStartRunner(Protocol):
    async def ainvoke(
        self,
        input: ConversationStartState,
    ) -> ConversationStartState:
        ...
