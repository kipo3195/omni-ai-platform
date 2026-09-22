from urllib.parse import quote
import logging

import httpx
from bs4 import BeautifulSoup

from app.features.trending.trending_models import TrendingTopic
from app.features.trending.enrichers.trending_context_enricher import (
    TrendingContextEnricher,
)

logger = logging.getLogger(__name__)

class GoogleNewsContextEnricher(TrendingContextEnricher):

    async def enrich(
        self,
        topics: list[TrendingTopic],
    ) -> list[TrendingTopic]:

        results = []
        logger.info(
            "google news enrichment started topics=%d",
            len(topics),
        )

        for topic in topics:
            try:
                enriched = await self._enrich_topic(topic)
                logger.info(
                    "trending topic enriched topic=%s news_items=%s",
                    topic.topic,
                    len(enriched.news_items),
                )
                results.append(enriched)

            except Exception:
                # enrichment 실패했다고 전체 refresh를 죽이지 않음
                logger.exception(
                    "failed to enrich trending topic topic=%s",
                    topic.topic,
                )

                results.append(topic)

        logger.info(
            "google news enrichment finished topics=%d enriched=%d",
            len(topics),
            len(results),
        )

        return results

    async def _enrich_topic(
        self,
        topic: TrendingTopic,
    ) -> TrendingTopic:

        news_items = await self._search_news(topic.topic)

        if not news_items:
            return topic

        return topic.model_copy(
            update={
                "news_items": news_items,
            }
        )

    async def _search_news(
    self,
    query: str,
    ) -> list[dict]:

        url = (
            "https://news.google.com/rss/search"
            f"?q={quote(query)}"
            "&hl=ko"
            "&gl=KR"
            "&ceid=KR:ko"
        )

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "xml",
        )

        items = []

        for item in soup.find_all("item")[:5]:
            items.append(
                {
                    "title": item.title.text
                    if item.title
                    else "",
                    "published": item.pubDate.text
                    if item.pubDate
                    else "",
                }
            )

        return items
