from app.features.conversation_start.conversation_start_state import ConversationStartState


async def analyze_recent_context(
    state: ConversationStartState,
) -> dict:

    messages = state.get("messages", [])

    # 아직 LLM은 붙이지 않고 mock 분석
    analyzed_context = {
        "topic": "배포 일정",
        "summary": "오늘 배포 일정과 진행 여부에 대한 대화",
    }

    return {
        "analyzed_context": analyzed_context
    }