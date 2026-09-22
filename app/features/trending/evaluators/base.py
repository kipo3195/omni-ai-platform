from abc import ABC, abstractmethod

from app.features.trending.trending_models import (
    EvaluatedTrendingTopic,
    TrendingBaseQuestion,
    TrendingTopic,
    TopicEvaluation,
    NewsContextEvaluation,
)


class TopicEvaluator(ABC):

    @abstractmethod
    async def evaluate(
        self,
        topics: list[TrendingTopic],
    ) -> list[TopicEvaluation]:
        pass


class NewsContextEvaluator(ABC):

    @abstractmethod
    async def evaluate(
        self,
        topics: list[TrendingTopic],
    ) -> list[NewsContextEvaluation]:
        pass


class TrendingBaseQuestionGenerator(ABC):

    @abstractmethod
    async def generate(
        self,
        topics: list[EvaluatedTrendingTopic],
    ) -> list[TrendingBaseQuestion]:
        pass
