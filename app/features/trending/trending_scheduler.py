import asyncio
import logging

from app.features.trending.trending_service import TrendingService

logger = logging.getLogger(__name__)

class TrendingScheduler:

    def __init__(
        self,
        trending_service: TrendingService,
        interval_seconds: int = 600,
    ):
        self.trending_service = trending_service
        self.interval_seconds = interval_seconds

    async def run(self):
        while True:
            await asyncio.sleep(self.interval_seconds)

            try:
                await self.trending_service.refresh()
            except Exception:
                logger.exception(
                    "Failed to refresh trending topics"
                )