# 어디에 저장할 것인가
from app.features.trending.trending_models import EvaluatedTrendingTopic


class TrendingRepository:

    def __init__(self):
        self._topics: list[EvaluatedTrendingTopic] = []

    async def find_all(
        self,
    ) -> list[EvaluatedTrendingTopic]:
        return self._topics.copy()

    async def replace(
        self,
        topics: list[EvaluatedTrendingTopic],
    ) -> None:
        self._topics = topics.copy()