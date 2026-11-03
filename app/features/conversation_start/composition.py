from app.features.conversation_start.conversation_start_graph import (
    create_conversation_start_graph,
)
from app.features.conversation_start.ports import (
    ConversationStartRunner,
    TrendingContextProvider,
)


def create_conversation_start_runner(
    *,
    trending_context_provider: TrendingContextProvider,
) -> ConversationStartRunner:
    return create_conversation_start_graph(
        trending_context_provider=trending_context_provider,
    )
