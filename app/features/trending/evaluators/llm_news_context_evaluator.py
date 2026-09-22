# app/features/trending/evaluators/llm_news_context_evaluator.py

import json
import logging
import asyncio
import time
from collections import deque

from pydantic import ValidationError

from app.features.trending.evaluators.base import NewsContextEvaluator
from app.features.trending.trending_models import (
    TrendingTopic,
    NewsContextEvaluation,
    NewsContextEvaluationResult,
)
from app.shared.llm.client.base import LlmClient
from app.shared.llm.model.request import LlmMessage, LlmRequest
from app.features.trending.prompts.news_context_evaluate_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_NEWS_ITEMS_PER_TOPIC = 3
NEWS_CONTEXT_BATCH_SIZE = 5
NEWS_CONTEXT_TPM_BUDGET = 7200
NEWS_CONTEXT_TPM_WINDOW_SECONDS = 60.0
NEWS_ITEM_PROMPT_FIELDS = (
    "title",
    "source",
)
MIN_RESPONSE_TOKENS = 1800
MAX_RESPONSE_TOKENS = 3000
RESPONSE_TOKENS_PER_TOPIC = 500


class LlmNewsContextEvaluator(NewsContextEvaluator):

    def __init__(
        self,
        llm_client: LlmClient,
    ):
        self.llm_client = llm_client
        self._token_requests = deque()

    async def evaluate(
        self,
        topics: list[TrendingTopic],
    ) -> list[NewsContextEvaluation]:

        if not topics:
            return []

        evaluations: list[NewsContextEvaluation] = []
        batch_size = self._resolve_batch_size(len(topics))

        for i in range(0, len(topics), batch_size):
            batch = topics[i:i + batch_size]

            batch_evaluations = await self._evaluate_batch(batch)

            if len(batch_evaluations) != len(batch):
                logger.warning(
                    "news context evaluation count mismatch "
                    "requested=%d evaluated=%d",
                    len(batch),
                    len(batch_evaluations),
                )

            evaluations.extend(batch_evaluations)

        return evaluations

    async def _evaluate_batch(
        self,
        topics: list[TrendingTopic],
    ) -> list[NewsContextEvaluation]:

        topic_data = [
            self._to_prompt_item(topic)
            for topic in topics
        ]

        user_prompt = json.dumps(
            {
                "topics": topic_data,
            },
            ensure_ascii=False,
        )
        prompt_tokens = self._estimate_token_count(SYSTEM_PROMPT + user_prompt)
        max_tokens = self._resolve_max_tokens(len(topics))
        estimated_request_tokens = prompt_tokens + max_tokens

        raw_news_item_count = sum(
            len(getattr(topic, "news_items", None) or [])
            for topic in topics
        )
        prompt_news_item_count = sum(
            len(item["news_items"])
            for item in topic_data
        )

        logger.info(
            "news context llm request prepared "
            "topics=%d raw_news_items=%d prompt_news_items=%d "
            "prompt_chars=%d approx_prompt_tokens=%d max_tokens=%d",
            len(topics),
            raw_news_item_count,
            prompt_news_item_count,
            len(user_prompt) + len(SYSTEM_PROMPT),
            prompt_tokens,
            max_tokens,
        )

        await self._wait_for_token_budget(estimated_request_tokens)

        response = await self.llm_client.generate(
            LlmRequest(
                messages=[
                    LlmMessage(
                        role="system",
                        content=SYSTEM_PROMPT,
                    ),
                    LlmMessage(
                        role="user",
                        content=user_prompt,
                    ),
                ],
                temperature=0.2,
                response_format={
                    "type": "json_object",
                },
                max_tokens=max_tokens,
            )
        )

        data = json.loads(response.content)

        try:
            result = NewsContextEvaluationResult(**data)
        except ValidationError:
            logger.exception(
                "failed to validate news context evaluation response "
                "topics=%s raw_response=%r",
                [topic.topic for topic in topics],
                response.content[:2000],
            )
            return []

        for evaluation in result.evaluations:
            logger.info(
                "news context evaluated "
                "topic=%s keep=%s "
                "generality=%.2f "
                "lightness=%.2f "
                "conversationality=%.2f "
                "sensitivity=%.2f "
                "smalltalk_fit=%.2f "
                "specificity=%.2f "
                "trend_context=%s ",
                evaluation.topic,
                evaluation.keep,
                evaluation.generality,
                evaluation.lightness,
                evaluation.conversationality,
                evaluation.sensitivity,
                evaluation.smalltalk_fit,
                evaluation.specificity,
                evaluation.trend_context,
            )

        return result.evaluations

    def _to_prompt_item(
        self,
        topic: TrendingTopic,
    ) -> dict:
        return {
            "topic": topic.topic,
            "category": topic.category,
            "summary": topic.summary,
            "keywords": topic.keywords,
            "news_items": self._get_news_items(topic),
        }

    def _get_news_items(
        self,
        topic: TrendingTopic,
    ) -> list[dict]:
        news_items = getattr(topic, "news_items", None)

        if not news_items:
            return []

        return [
            self._to_prompt_news_item(news_item)
            for news_item in news_items[:MAX_NEWS_ITEMS_PER_TOPIC]
        ]

    def _to_prompt_news_item(
        self,
        news_item: dict,
    ) -> dict:
        return {
            key: value
            for key in NEWS_ITEM_PROMPT_FIELDS
            if (value := news_item.get(key))
        }

    def _estimate_token_count(
        self,
        text: str,
    ) -> int:
        return max(1, len(text) // 4)

    def _resolve_max_tokens(
        self,
        topic_count: int,
    ) -> int:
        return min(
            MAX_RESPONSE_TOKENS,
            max(
                MIN_RESPONSE_TOKENS,
                topic_count * RESPONSE_TOKENS_PER_TOPIC,
            ),
        )

    async def _wait_for_token_budget(
        self,
        estimated_request_tokens: int,
    ) -> None:
        now = time.monotonic()
        self._discard_expired_token_requests(now)

        used_tokens = sum(
            tokens
            for _, tokens in self._token_requests
        )

        if used_tokens + estimated_request_tokens > NEWS_CONTEXT_TPM_BUDGET:
            oldest_request_at, _ = self._token_requests[0]
            wait_seconds = (
                oldest_request_at
                + NEWS_CONTEXT_TPM_WINDOW_SECONDS
                - now
            )

            logger.info(
                "news context llm token budget waiting "
                "used_tokens=%d request_tokens=%d budget=%d wait_seconds=%.1f",
                used_tokens,
                estimated_request_tokens,
                NEWS_CONTEXT_TPM_BUDGET,
                wait_seconds,
            )

            await asyncio.sleep(max(0.0, wait_seconds))

            now = time.monotonic()
            self._discard_expired_token_requests(now)

        self._token_requests.append(
            (
                time.monotonic(),
                estimated_request_tokens,
            )
        )

    def _discard_expired_token_requests(
        self,
        now: float,
    ) -> None:
        while self._token_requests:
            requested_at, _ = self._token_requests[0]

            if now - requested_at < NEWS_CONTEXT_TPM_WINDOW_SECONDS:
                break

            self._token_requests.popleft()

    def _resolve_batch_size(
        self,
        topic_count: int,
    ) -> int:
        if topic_count <= 20:
            return NEWS_CONTEXT_BATCH_SIZE

        return NEWS_CONTEXT_BATCH_SIZE
