from app.features.trending.trending_service import TrendingService
from app.features.conversation_start.conversation_start_state import ConversationStartState

def create_load_trending_context_node(
    trending_service: TrendingService,
):

    async def load_trending_context(
        state: ConversationStartState,
    ) -> dict:

        topics = await trending_service.get_context(
            limit=10,
        )

        return {
            "trending_context": topics,
        }

    return load_trending_context