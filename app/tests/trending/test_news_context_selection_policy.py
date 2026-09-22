from app.features.trending.policies.news_context_selection_policy import (
    NewsContextSelectionPolicy,
)
from app.features.trending.trending_models import (
    NewsContextEvaluation,
    TrendingTopic,
)


def test_news_context_selection_policy_allows_lower_scores():
    topic = build_topic("두바이 초콜릿")
    evaluation = build_evaluation(
        topic="두바이 초콜릿",
        generality=0.4,
        lightness=0.4,
        conversationality=0.4,
        sensitivity=0.2,
        specificity=0.4,
        smalltalk_fit=0.4,
    )

    selected = NewsContextSelectionPolicy().select(
        topics=[topic],
        evaluations=[evaluation],
    )

    assert len(selected) == 1
    assert selected[0].topic == "두바이 초콜릿"


def test_news_context_selection_policy_still_rejects_llm_keep_false():
    topic = build_topic("두바이 초콜릿")
    evaluation = build_evaluation(
        topic="두바이 초콜릿",
        keep=False,
    )

    selected = NewsContextSelectionPolicy().select(
        topics=[topic],
        evaluations=[evaluation],
    )

    assert selected == []


def test_news_context_selection_policy_still_rejects_high_sensitivity():
    topic = build_topic("민감한 이슈")
    evaluation = build_evaluation(
        topic="민감한 이슈",
        sensitivity=0.7,
    )

    selected = NewsContextSelectionPolicy().select(
        topics=[topic],
        evaluations=[evaluation],
    )

    assert selected == []


def build_topic(
    topic: str,
) -> TrendingTopic:
    return TrendingTopic(
        topic=topic,
        category="culture",
        summary="요약",
        keywords=[topic],
    )


def build_evaluation(
    topic: str,
    generality: float = 0.8,
    lightness: float = 0.8,
    conversationality: float = 0.8,
    sensitivity: float = 0.1,
    specificity: float = 0.8,
    smalltalk_fit: float = 0.8,
    keep: bool = True,
) -> NewsContextEvaluation:
    return NewsContextEvaluation(
        topic=topic,
        trend_context="뉴스 맥락",
        generality=generality,
        lightness=lightness,
        conversationality=conversationality,
        sensitivity=sensitivity,
        specificity=specificity,
        smalltalk_fit=smalltalk_fit,
        keep=keep,
        reject_reason=None,
    )
