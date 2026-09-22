import logging

from app.features.trending.trending_models import (
    TopicEvaluation,
    TrendingTopic,
)

logger = logging.getLogger(__name__)

class TrendingTopicSelectionPolicy:
    def select_topics(
        self,
        topics: list[TrendingTopic],
        evaluations: list[TopicEvaluation],
    ) -> list[TrendingTopic]:

        evaluation_map = {
            evaluation.topic: evaluation
            for evaluation in evaluations
        }

        selected_topics: list[TrendingTopic] = []

        for topic in topics:
            evaluation = evaluation_map.get(topic.topic)

            if evaluation is None:
                logger.warning(
                    "topic evaluation not found topic=%s",
                    topic.topic,
                )
                continue

            score = self.calculate_score(evaluation)

            if not self.should_keep(evaluation, score):
                logger.info(
                    "trending topic rejected by topic prefilter "
                    "topic=%s score=%.3f "
                    "generality=%.2f "
                    "specificity=%.2f "
                    "searchability=%.2f "
                    "topic_quality=%.2f "
                    "obvious_sensitivity=%.2f",
                    topic.topic,
                    score,
                    evaluation.generality,
                    evaluation.specificity,
                    evaluation.searchability,
                    evaluation.topic_quality,
                    evaluation.obvious_sensitivity,
                )
                continue

            logger.info(
                "trending topic selected by topic prefilter "
                "topic=%s score=%.3f "
                "generality=%.2f "
                "specificity=%.2f "
                "searchability=%.2f "
                "topic_quality=%.2f "
                "obvious_sensitivity=%.2f",
                topic.topic,
                score,
                evaluation.generality,
                evaluation.specificity,
                evaluation.searchability,
                evaluation.topic_quality,
                evaluation.obvious_sensitivity,
            )
            selected_topics.append(topic)

        return selected_topics

    def calculate_score(
        self,
        evaluation: TopicEvaluation,
    ) -> float:
        return (
            evaluation.topic_quality * 0.35
            + evaluation.searchability * 0.25
            + evaluation.specificity * 0.20
            + evaluation.generality * 0.10
            + (1.0 - evaluation.obvious_sensitivity) * 0.10
        )

    def should_keep(
        self,
        evaluation: TopicEvaluation,
        score: float,
    ) -> bool:
        if evaluation.obvious_sensitivity >= 0.6:
            return False

        if evaluation.topic_quality < 0.5:
            return False

        if evaluation.searchability < 0.5:
            return False

        if evaluation.specificity < 0.4:
            return False

        return score >= 0.55
