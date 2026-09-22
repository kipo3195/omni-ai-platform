from abc import ABC, abstractmethod

from app.features.trending.trending_models import TrendingTopic


class TrendingProvider(ABC):

    @abstractmethod
    async def fetch(self) -> list[TrendingTopic]:
        pass