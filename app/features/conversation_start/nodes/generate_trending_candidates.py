import logging
from typing import Any

from app.features.conversation_start.conversation_start_state import ConversationStartState

logger = logging.getLogger(__name__)


def create_generate_trending_candidates_node(
):

    async def generate_trending_candidates(
        state: ConversationStartState,
    ) -> dict:
        options = state.get("options")
        max_suggestions = options.max_suggestions if options else 3

        trending_context = state.get("trending_context")
        logger.warning("trending_context = %s", trending_context)

        if not trending_context:
            logger.warning(
                "Trending context is empty. session_id=%s",
                state.get("session_id"),
            )
            return {
                "candidate_messages": []
            }
        
        candidate_messages = build_candidates_from_base_questions(
            trending_context=trending_context,
            max_suggestions=max_suggestions,
        )

        return {
            "candidate_messages": candidate_messages
        }

    return generate_trending_candidates


def build_candidates_from_base_questions(
    trending_context: list[Any],
    max_suggestions: int,
) -> list[dict]:
    candidates = []

    for item in trending_context:
        topic = get_value(item, "topic")
        question = get_value(item, "base_question")

        if not topic or not question:
            continue

        question = str(question).strip()
        if not question:
            continue

        candidates.append({
            "topic": str(topic),
            "question": question,
        })

        if len(candidates) == max_suggestions:
            break

    return candidates


def get_value(
    item: Any,
    key: str,
) -> Any:
    if isinstance(item, dict):
        return item.get(key)

    return getattr(item, key, None)
