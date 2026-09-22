import asyncio

from app.features.conversation_start.conversation_start_schemas import (
    ConversationStartRequest,
    ConversationStartResponse,
    RequestOptions,
    SuggestionType,
)
from app.features.conversation_start.nodes.generate_trending_candidates import (
    build_candidates_from_base_questions,
    create_generate_trending_candidates_node,
)
from app.features.trending.trending_models import EvaluatedTrendingTopic


def test_conversation_start_request_accepts_options():
    request = ConversationStartRequest(
        session_id="session-1",
        user_id="user-1",
        room_id="room-1",
        suggestion_type=SuggestionType.RECENT_CONTEXT,
        options={
            "max_suggestions": 5,
            "max_length": 80,
            "language": "en",
        },
    )

    assert request.options.max_suggestions == 5
    assert request.options.max_length == 80
    assert request.options.language == "en"


def test_conversation_start_response_accepts_topic_question_suggestions():
    response = ConversationStartResponse(
        session_id="session-1",
        suggestions=[
            {
                "topic": "점심 메뉴",
                "question": "오늘 점심 뭐 드실 예정이세요?",
            }
        ],
    )

    assert response.suggestions[0].topic == "점심 메뉴"
    assert response.suggestions[0].question == "오늘 점심 뭐 드실 예정이세요?"


def test_generate_trending_candidates_uses_saved_base_questions():
    generate_trending_candidates = create_generate_trending_candidates_node()

    result = asyncio.run(
        generate_trending_candidates(
            {
                "options": RequestOptions(max_suggestions=2),
                "trending_context": [
                    build_evaluated_topic(
                        topic="두바이 초콜릿",
                        base_question="요즘 두바이 초콜릿 신제품 많이 보이던데 먹어봤어요?",
                    ),
                    build_evaluated_topic(
                        topic="AI 이미지",
                        base_question="요즘 AI 이미지 앱 많이 보이던데 써본 적 있어요?",
                    ),
                    build_evaluated_topic(
                        topic="새 영화",
                        base_question="요즘 새로 개봉한 영화 중에 보고 싶은 거 있어요?",
                    ),
                ],
            }
        )
    )

    assert result["candidate_messages"] == [
        {
            "topic": "두바이 초콜릿",
            "question": "요즘 두바이 초콜릿 신제품 많이 보이던데 먹어봤어요?",
        },
        {
            "topic": "AI 이미지",
            "question": "요즘 AI 이미지 앱 많이 보이던데 써본 적 있어요?",
        },
    ]


def test_build_candidates_from_base_questions_skips_missing_question():
    result = build_candidates_from_base_questions(
        trending_context=[
            build_evaluated_topic(
                topic="두바이 초콜릿",
                base_question="요즘 두바이 초콜릿 신제품 많이 보이던데 먹어봤어요?",
            ),
            build_evaluated_topic(
                topic="AI 이미지",
                base_question=None,
            ),
        ],
        max_suggestions=3,
    )

    assert result == [
        {
            "topic": "두바이 초콜릿",
            "question": "요즘 두바이 초콜릿 신제품 많이 보이던데 먹어봤어요?",
        }
    ]


def test_build_candidates_from_base_questions_accepts_dicts():
    result = build_candidates_from_base_questions(
        trending_context=[
            {
                "topic": "AI 이미지",
                "base_question": "요즘 AI 이미지 앱 많이 보이던데 써본 적 있어요?",
            }
        ],
        max_suggestions=3,
    )

    assert result == [
        {
            "topic": "AI 이미지",
            "question": "요즘 AI 이미지 앱 많이 보이던데 써본 적 있어요?",
        }
    ]


def build_evaluated_topic(
    topic: str,
    base_question: str | None,
) -> EvaluatedTrendingTopic:
    return EvaluatedTrendingTopic(
        topic=topic,
        category="culture",
        summary="요약",
        keywords=[topic],
        generality=0.8,
        lightness=0.8,
        conversationality=0.8,
        sensitivity=0.1,
        specificity=0.8,
        smalltalk_fit=0.8,
        score=0.8,
        trend_context="트렌드 맥락",
        base_question=base_question,
    )
