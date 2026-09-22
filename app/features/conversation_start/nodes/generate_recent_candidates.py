from app.features.conversation_start.conversation_start_state import ConversationStartState



async def generate_recent_candidates(
    state: ConversationStartState,
) -> dict:

    analyzed_context = state.get(
        "analyzed_context",
        {},
    )

    # 딕셔너리.get("키", 기본값)
    topic = analyzed_context.get(
        "topic", 
        "최근 대화", #default value 
    )

    return {
        "candidate_messages": [
            {
                "topic": topic,
                "question": f"{topic} 관련해서 진행 상황은 어떠세요?",
            },
            {
                "topic": topic,
                "question": f"{topic} 관련해서 추가로 확인할 내용 있을까요?",
            },
            {
                "topic": topic,
                "question": f"{topic} 일정은 그대로 진행하시나요?",
            },
        ]
    }
