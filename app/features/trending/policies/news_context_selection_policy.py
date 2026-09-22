import logging

from app.features.trending.trending_models import (
    EvaluatedTrendingTopic,
    NewsContextEvaluation,
    TrendingTopic,
)

logger = logging.getLogger(__name__)


class NewsContextSelectionPolicy:

    def select(
        self,
        topics: list[TrendingTopic],
        evaluations: list[NewsContextEvaluation],
    ) -> list[EvaluatedTrendingTopic]:

        evaluation_map = {
            evaluation.topic: evaluation
            for evaluation in evaluations
        }

        selected_topics: list[EvaluatedTrendingTopic] = []

        for topic in topics:
            evaluation = evaluation_map.get(topic.topic)

            if evaluation is None:
                logger.warning(
                    "news context evaluation not found topic=%s",
                    topic.topic,
                )
                continue

            score = self.calculate_score(evaluation)

            if not evaluation.keep:
                logger.info(
                    "news context topic rejected by llm "
                    "topic=%s reason=%s score=%.3f",
                    topic.topic,
                    evaluation.reject_reason,
                    score,
                )
                continue

            if not self.should_store(evaluation, score):
                logger.info(
                    "news context topic rejected by policy "
                    "topic=%s score=%.3f "
                    "generality=%.2f "
                    "lightness=%.2f "
                    "conversationality=%.2f "
                    "sensitivity=%.2f "
                    "smalltalk_fit=%.2f "
                    "specificity=%.2f",
                    topic.topic,
                    score,
                    evaluation.generality,
                    evaluation.lightness,
                    evaluation.conversationality,
                    evaluation.sensitivity,
                    evaluation.smalltalk_fit,
                    evaluation.specificity,
                )
                continue

            logger.info(
                "news context topic selected "
                "topic=%s score=%.3f "
                "generality=%.2f "
                "lightness=%.2f "
                "conversationality=%.2f "
                "sensitivity=%.2f "
                "smalltalk_fit=%.2f "
                "specificity=%.2f "
                "trend_context=%s",
                topic.topic,
                score,
                evaluation.generality,
                evaluation.lightness,
                evaluation.conversationality,
                evaluation.sensitivity,
                evaluation.smalltalk_fit,
                evaluation.specificity,
                evaluation.trend_context,
            )
            selected_topics.append(
                EvaluatedTrendingTopic(
                    topic=topic.topic,
                    category=topic.category,
                    summary=topic.summary,
                    keywords=topic.keywords,
                    generality=evaluation.generality,
                    lightness=evaluation.lightness,
                    conversationality=evaluation.conversationality,
                    sensitivity=evaluation.sensitivity,
                    smalltalk_fit=evaluation.smalltalk_fit,
                    specificity=evaluation.specificity,
                    score=score,
                    trend_context=evaluation.trend_context,
                )
            )

        return selected_topics

    def calculate_score(
        self,
        evaluation: NewsContextEvaluation,
    ) -> float:
        return (
            evaluation.smalltalk_fit * 0.20
            + evaluation.conversationality * 0.20
            + evaluation.lightness * 0.15
            + evaluation.generality * 0.15
            + evaluation.specificity * 0.15
            + (1.0 - evaluation.sensitivity) * 0.15
        )

    def should_store(
        self,
        evaluation: NewsContextEvaluation,
        score: float,
    ) -> bool:
        if evaluation.sensitivity >= 0.7:
            return False

        if evaluation.conversationality < 0.3:
            return False

        if evaluation.generality < 0.3:
            return False

        if evaluation.lightness < 0.3:
            return False

        if evaluation.smalltalk_fit < 0.3:
            return False

        if evaluation.specificity < 0.3:
            return False

        return score >= 0.45
