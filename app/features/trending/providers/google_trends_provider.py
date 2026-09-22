import logging
import re
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag

import httpx

from app.features.trending.trending_models import TrendingTopic
from app.features.trending.providers.provider import TrendingProvider


logger = logging.getLogger(__name__)


class GoogleTrendingProvider(TrendingProvider):

    TRENDING_URL = "https://trends.google.com/trending"

    def __init__(
        self,
        limit: int,
    ):
        self.limit = limit

    async def fetch(self) -> list[TrendingTopic]:

        raw_trends = await self._fetch_raw_trends()

        topics: list[TrendingTopic] = []

        for item in raw_trends[:self.limit]:
            try:
                topics.append(
                    self._to_topic(item)
                )

            except Exception:
                logger.exception(
                    "failed to convert google trend item: %s",
                    item,
                )

        logger.info(
            "google trends fetched topics count=%d limit=%d",
            len(topics),
            self.limit,
        )

        return topics

    async def _fetch_raw_trends(
        self,
    ) -> list[dict]:

        params = {
            "geo": "KR",
            "hours": "24",
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
        }

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
        ) as client:

            # 구글 트렌드 조회 파라미터 
            params = {
                "geo": "KR",
                "hours": "4",
                "sort": "search-volume",
            }

            response = await client.get(
                self.TRENDING_URL,
                params=params,
                headers=headers,
            )

            response.raise_for_status()

            logger.info(
                "google trends response status=%s length=%d",
                response.status_code,
                len(response.content),
            )

        return self._parse_html(
            response.text
        )

    def _parse_html(
        self,
        html: str,
    ) -> list[dict]:

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        trends: list[dict] = []

        # 실제 트렌드 row만 조회
        rows = soup.select(
            "tr[data-row-id]"
        )

        logger.info(
            "google trends row count=%d",
            len(rows),
        )

        for row in rows:

            cells = row.find_all(
                "td"
            )

            if len(cells) < 4:
                continue

            # cell[1]
            # ex)
            # 과태료 20K+ searches · trending_up Active · 3h ago
            topic_text = cells[1].get_text(
                " ",
                strip=True,
            )

            title = self._extract_title(
                topic_text
            )

            if not title:
                continue

            # cell[2]
            # ex)
            # 20K+ arrow_upward 1,000%
            traffic = cells[2].get_text(
                " ",
                strip=True,
            )

            # cell[3]
            # ex)
            # 3 hours ago trending_up Active
            trend_time = cells[3].get_text(
                " ",
                strip=True,
            )

            # cell[4]
            # 관련 검색어
            keywords: list[str] = []

            if len(cells) > 4:
                keywords = self._extract_related_keywords(
                    cells[4]
                )

            trends.append(
                {
                    "title": title,
                    "traffic": traffic,
                    "trend_time": trend_time,
                    "summary": "",
                    "keywords": keywords,
                }
            )

            logger.debug(
                "google trend parsed title=%s keywords=%s",
                title,
                keywords,
            )

            if len(trends) >= self.limit:
                break

        logger.info(
            "google trends parsed count=%d",
            len(trends),
        )

        return trends

    def _extract_title(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        # ex)
        # "송하예 20K+ searches · trending_up Active · 18h ago"
        # ->
        # "송하예"

        title = re.sub(
            r"\s+\d+(?:\.\d+)?[KMB]?\+\s+searches.*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return title.strip()

    def _extract_related_keywords(
        self,
        cell: Tag,
    ) -> list[str]:

        keywords: list[str] = []

        links = cell.find_all(
            "a",
            href=True,
        )

        for link in links:

            href = link.get(
                "href",
                "",
            )

            keyword = self._extract_query_from_href(
                href
            )

            # href에서 검색어를 못 찾으면
            # 링크의 실제 표시 텍스트를 fallback으로 사용
            if not keyword:
                keyword = link.get_text(
                    " ",
                    strip=True,
                )

            keyword = keyword.strip()

            if not keyword:
                continue

            # UI 문자열 제외 -> 웹페이지를 그대로 가져와서 파싱하므로 
            if keyword.lower() in {
                "explore",
                "search term",
                "query_stats",
            }:
                continue

            # 중복 제거
            if keyword not in keywords:
                keywords.append(
                    keyword
                )

        return keywords[:5]

    def _extract_query_from_href(
        self,
        href: str,
    ) -> str:

        if not href:
            return ""

        try:
            parsed = urlparse(
                href
            )

            params = parse_qs(
                parsed.query
            )

            queries = params.get(
                "q"
            )

            if not queries:
                return ""

            return queries[0].strip()

        except Exception:
            logger.debug(
                "failed to parse trend related href=%s",
                href,
            )

            return ""

    def _to_topic(
        self,
        item: dict,
    ) -> TrendingTopic:

        return TrendingTopic(
            topic=item["title"],
            category="unknown",
            summary=item.get(
                "summary",
                "",
            ),
            keywords=item.get(
                "keywords",
                [],
            ),
        )


# class GoogleTrendingProvider(TrendingProvider):

#     RSS_URL = "https://trends.google.com/trending/rss"

#     GOOGLE_NS = {
#         "ht": "https://trends.google.com/trending/rss"
#     }

#     def __init__(
#             self,
#             limit: int,
#         ):
#         self.limit = limit
    

#     async def fetch(self) -> list[TrendingTopic]:
      
#         raw_trends = await self._fetch_raw_trends()

#         topics: list[TrendingTopic] = []

#         for item in raw_trends[:self.limit]:
#             try:
#                 topic = self._to_topic(item)
#                 topics.append(topic)

#             except Exception:
#                 logger.exception(
#                     "failed to convert google trend item: %s",
#                     item,
#                 )

#         logger.info(
#             "google trends fetched topics count=%d",
#             len(topics),
#         )

#         return topics

#     async def _fetch_raw_trends(self) -> list[dict]:

#         params = {
#             "geo": "KR",
#         }

#         headers = {
#             "User-Agent": (
#                 "Mozilla/5.0 "
#                 "(Macintosh; Intel Mac OS X 10_15_7) "
#                 "AppleWebKit/537.36 "
#                 "(KHTML, like Gecko) "
#                 "Chrome/151.0.0.0 Safari/537.36"
#             ),
#         }

#         async with httpx.AsyncClient(
#             timeout=10.0,
#             follow_redirects=True,
#         ) as client:

#             response = await client.get(
#                 self.RSS_URL,
#                 params=params,
#                 headers=headers,
#             )

#             logger.info(
#                 "google trends rss response status=%s length=%d",
#                 response.status_code,
#                 len(response.content),
#             )

#             response.raise_for_status()

#         return self._parse_rss(
#             response.text
#         )

#     def _parse_rss(
#         self,
#         xml_text: str,
#     ) -> list[dict]:

#         root = ET.fromstring(
#             xml_text
#         )

#         trends: list[dict] = []

#         items = root.findall(
#             ".//item"
#         )

#         logger.info(
#             "google trends rss item count=%d",
#             len(items),
#         )

#         for item in items:

#             title = self._get_text(
#                 item,
#                 "title",
#             )

#             if not title:
#                 continue

#             traffic = self._get_text(
#                 item,
#                 "ht:approx_traffic",
#             )

#             pub_date = self._get_text(
#                 item,
#                 "pubDate",
#             )

#             news_items = self._parse_news_items(
#                 item
#             )

#             keywords = self._extract_keywords(
#                 news_items
#             )

#             summary = self._build_summary(
#                 news_items
#             )

#             trends.append(
#                 {
#                     "title": title,
#                     "traffic": traffic,
#                     "pub_date": pub_date,
#                     "keywords": keywords,
#                     "summary": summary,
#                 }
#             )

#         return trends

#     def _parse_news_items(
#         self,
#         item: ET.Element,
#     ) -> list[dict]:

#         news_items: list[dict] = []

#         elements = item.findall(
#             "ht:news_item",
#             self.GOOGLE_NS,
#         )

#         for element in elements:

#             news_title = self._get_text(
#                 element,
#                 "ht:news_item_title",
#             )

#             news_source = self._get_text(
#                 element,
#                 "ht:news_item_source",
#             )

#             news_url = self._get_text(
#                 element,
#                 "ht:news_item_url",
#             )

#             news_items.append(
#                 {
#                     "title": news_title,
#                     "source": news_source,
#                     "url": news_url,
#                 }
#             )

#         return news_items

#     def _extract_keywords(
#         self,
#         news_items: list[dict],
#     ) -> list[str]:

#         keywords: list[str] = []

#         for news in news_items:

#             title = news.get("title")

#             if not title:
#                 continue

#             keywords.append(
#                 title
#             )

#         return keywords[:5]

#     def _build_summary(
#         self,
#         news_items: list[dict],
#     ) -> str:

#         if not news_items:
#             return ""

#         first_news = news_items[0]

#         return first_news.get(
#             "title",
#             "",
#         )

#     def _get_text(
#         self,
#         element: ET.Element,
#         path: str,
#     ) -> str:

#         target = element.find(
#             path,
#             self.GOOGLE_NS,
#         )

#         if target is None:
#             return ""

#         return (
#             target.text or ""
#         ).strip()

#     def _to_topic(
#         self,
#         item: dict,
#     ) -> TrendingTopic:

#         return TrendingTopic(
#             topic=item["title"],
#             category="unknown",
#             summary=item.get(
#                 "summary",
#                 "",
#             ),
#             keywords=item.get(
#                 "keywords",
#                 [],
#             ),
#         )