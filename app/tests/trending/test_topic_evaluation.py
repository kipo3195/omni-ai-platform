import asyncio
import json

from app.features.trending.evaluators.llm_topic_evaluator import LlmTopicEvaluator
from app.features.trending.policies.trending_topic_selection_policy import (
    TrendingTopicSelectionPolicy,
)
from app.features.trending.trending_models import TopicEvaluation, TrendingTopic
from app.shared.llm.model.response import LlmResponse


class FakeTopicEvaluationLlmClient:

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
                            "generality": 0.8,
                            "specificity": 0.8,
                            "searchability": 0.8,
                            "topic_quality": 0.8,
                            "obvious_sensitivity": 0.1,
                        }
                        for item in payload["topics"]
                    ]
                },
                ensure_ascii=False,
            )
        )


def test_topic_evaluation_accepts_prefilter_scores():
    evaluation = TopicEvaluation(
        topic="두바이 초콜릿",
        generality=0.8,
        specificity=0.8,
        searchability=0.9,
        topic_quality=0.9,
        obvious_sensitivity=0.1,
    )

    assert evaluation.searchability == 0.9
    assert evaluation.topic_quality == 0.9


def test_topic_selection_policy_uses_prefilter_scores():
    topics = [
        build_topic("두바이 초콜릿"),
        build_topic("민감한 이슈"),
    ]
    evaluations = [
        TopicEvaluation(
            topic="두바이 초콜릿",
            generality=0.7,
            specificity=0.8,
            searchability=0.9,
            topic_quality=0.9,
            obvious_sensitivity=0.1,
        ),
        TopicEvaluation(
            topic="민감한 이슈",
            generality=0.9,
            specificity=0.9,
            searchability=0.9,
            topic_quality=0.9,
            obvious_sensitivity=0.8,
        ),
    ]

    selected = TrendingTopicSelectionPolicy().select_topics(
        topics=topics,
        evaluations=evaluations,
    )

    assert selected == [topics[0]]


def test_llm_topic_evaluator_batches_up_to_twenty_topics_once():
    llm_client = FakeTopicEvaluationLlmClient()
    evaluator = LlmTopicEvaluator(llm_client=llm_client)

    evaluations = asyncio.run(
        evaluator.evaluate([
            build_topic(f"topic-{index}")
            for index in range(20)
        ])
    )

    assert len(evaluations) == 20
    assert len(llm_client.requests) == 1


def test_llm_topic_evaluator_batches_over_twenty_topics_by_ten():
    llm_client = FakeTopicEvaluationLlmClient()
    evaluator = LlmTopicEvaluator(llm_client=llm_client)

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
    assert batch_sizes == [10, 10, 1]


def build_topic(
    topic: str,
) -> TrendingTopic:
    return TrendingTopic(
        topic=topic,
        category="culture",
        summary="요약",
        keywords=[topic],
    )
