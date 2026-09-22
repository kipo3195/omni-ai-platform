import asyncio
import json

from app.features.trending.evaluators.llm_news_context_evaluator import (
    LlmNewsContextEvaluator,
)
from app.features.trending.trending_models import TrendingTopic
from app.shared.llm.model.response import LlmResponse


class FakeNewsContextLlmClient:

    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        payload = json.loads(request.messages[1].content)
        return LlmResponse(
            content=json.dumps(
                {
                    "evaluations": [
                        {
                            "topic": item["topic"],
                            "trend_context": "뉴스 맥락",
                            "generality": 0.8,
                            "lightness": 0.8,
                            "conversationality": 0.8,
                            "sensitivity": 0.1,
                            "specificity": 0.8,
                            "smalltalk_fit": 0.8,
                            "keep": True,
                            "reject_reason": None,
                        }
                        for item in payload["topics"]
                    ]
                },
                ensure_ascii=False,
            )
        )


def test_news_context_evaluator_batches_twenty_topics_by_five():
    llm_client = FakeNewsContextLlmClient()
    evaluator = LlmNewsContextEvaluator(llm_client=llm_client)

    evaluations = asyncio.run(
        evaluator.evaluate([
            build_topic(f"topic-{index}")
            for index in range(20)
        ])
    )

    assert len(evaluations) == 20
    assert len(llm_client.requests) == 4


def test_news_context_evaluator_batches_over_twenty_topics_by_five():
    llm_client = FakeNewsContextLlmClient()
    evaluator = LlmNewsContextEvaluator(llm_client=llm_client)

    evaluations = asyncio.run(
        evaluator.evaluate([
            build_topic(f"topic-{index}")
            for index in range(21)
        ])
    )

    batch_sizes = [
        len(json.loads(request.messages[1].content)["topics"])
        for request in llm_client.requests
    ]

    assert len(evaluations) == 21
    assert batch_sizes == [5, 5, 5, 5, 1]


def test_news_context_evaluator_limits_news_items_for_prompt():
    llm_client = FakeNewsContextLlmClient()
    evaluator = LlmNewsContextEvaluator(llm_client=llm_client)

    asyncio.run(
        evaluator.evaluate([
            TrendingTopic(
                topic="topic",
                category="culture",
                summary="요약",
                keywords=["topic"],
                news_items=[
                    {
                        "title": f"뉴스 {index}",
                        "source": "언론사",
                        "published": "Tue, 15 Sep 2026 00:00:00 GMT",
                        "description": "프롬프트에는 들어가지 않아야 하는 긴 설명",
                    }
                    for index in range(5)
                ],
            )
        ])
    )

    payload = json.loads(llm_client.requests[0].messages[1].content)
    news_items = payload["topics"][0]["news_items"]

    assert news_items == [
        {
            "title": "뉴스 0",
            "source": "언론사",
        },
        {
            "title": "뉴스 1",
            "source": "언론사",
        },
        {
            "title": "뉴스 2",
            "source": "언론사",
        },
    ]


def build_topic(
    topic: str,
) -> TrendingTopic:
    return TrendingTopic(
        topic=topic,
        category="culture",
        summary="요약",
        keywords=[topic],
        news_items=[
            {
                "title": f"{topic} 뉴스",
            }
        ],
    )
