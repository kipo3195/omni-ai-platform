"""Apply user style preferences."""


async def apply_user_style(
    state: ConversationStartState
) -> dict:

    result = await user_style_service.rewrite(
        user_id=state["user_id"],
        messages=state["candidate_messages"],
    )

    return {
        "styled_messages": result
    }

# 추후 shared 쪽으로 이관할것 