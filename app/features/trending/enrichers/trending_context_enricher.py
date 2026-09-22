from abc import ABC, abstractmethod

from app.features.trending.trending_models import TrendingTopic



class TrendingContextEnricher(ABC):
    @abstractmethod
    async def enrich(
        self,
        topics: list[TrendingTopic],
    ) -> list[TrendingTopic]:
        pass