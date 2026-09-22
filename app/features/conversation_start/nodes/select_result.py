"""Select the best result from validated candidates."""


from app.features.conversation_start.conversation_start_state import ConversationStartState


async def select_result(
    state: ConversationStartState,
) -> dict:
    candidates = state.get("candidate_messages", [])
    options = state.get("options")
    max_suggestions = options.max_suggestions if options else 3

    return {
        "selected_messages": candidates[:max_suggestions]
    }
