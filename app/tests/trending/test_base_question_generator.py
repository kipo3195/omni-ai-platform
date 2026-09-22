import asyncio
import json

from app.features.trending.generators.llm_base_question_generator import (
    LlmTrendingBaseQuestionGenerator,
)
from app.features.trending.trending_models import EvaluatedTrendingTopic
from app.shared.llm.model.response import LlmResponse


class FakeLlmClient:

    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return LlmResponse(
            content=json.dumps(
                {
                    "questions": [
                        {
                            "topic": "두바이 초콜릿",
                            "question": "요즘 두바이 초콜릿 신제품 많이 보이던데 먹어봤어요?",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        )


def test_base_question_generator_uses_selected_evaluated_topics():
    llm_client = FakeLlmClient()
    generator = LlmTrendingBaseQuestionGenerator(llm_client=llm_client)

    questions = asyncio.run(
        generator.generate(
            [
                EvaluatedTrendingTopic(
                    topic="두바이 초콜릿",
                    category="food",
                    summary="SNS에서 관련 디저트가 유행",
                    keywords=["두바이 초콜릿", "디저트"],
                    generality=0.8,
                    lightness=0.8,
                    conversationality=0.9,
                    sensitivity=0.1,
                    specificity=0.8,
                    smalltalk_fit=0.9,
                    score=0.85,
                    trend_context="최근 카페와 편의점 신제품 출시로 관심 증가",
                )
            ]
        )
    )

    assert len(llm_client.requests) == 1
    assert questions[0].topic == "두바이 초콜릿"
    assert questions[0].question == "요즘 두바이 초콜릿 신제품 많이 보이던데 먹어봤어요?"
    assert "최근 카페와 편의점 신제품 출시로 관심 증가" in llm_client.requests[0].messages[1].content
