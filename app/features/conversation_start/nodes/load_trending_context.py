from app.features.conversation_start.ports import TrendingContextProvider
from app.features.conversation_start.conversation_start_state import ConversationStartState


def create_load_trending_context_node(
    context_provider: TrendingContextProvider,
):

    async def load_trending_context(
        state: ConversationStartState,
    ) -> dict:

        topics = await context_provider.get_context(
            limit=10,
        )

        return {
            "trending_context": topics,
        }

    return load_trending_context
