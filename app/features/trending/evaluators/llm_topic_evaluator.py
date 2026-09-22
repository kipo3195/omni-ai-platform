import json
import logging

from app.features.trending.trending_models import (
    TrendingTopic,
    TopicEvaluation,
    TopicEvaluationResult,
)

from app.shared.llm.client.base import LlmClient

from app.shared.llm.model.request import LlmMessage, LlmRequest
from app.features.trending.prompts.trending_evaluate_prompt import (SYSTEM_PROMPT)

logger = logging.getLogger(__name__)

class LlmTopicEvaluator:

    def __init__(
            self, 
        llm_client: LlmClient):
        self.llm_client = llm_client

    async def evaluate(
    self,
    topics: list[TrendingTopic],
    ) -> list[TopicEvaluation]:

        if not topics:
            return []

        batch_size = self._resolve_batch_size(len(topics))
        evaluations: list[TopicEvaluation] = []

        for i in range(0, len(topics), batch_size):
            batch = topics[i:i + batch_size]

            batch_evaluations = await self._evaluate_batch(batch)

            if len(batch_evaluations) != len(batch):
                logger.warning(
                    "topic evaluation count mismatch "
                    "requested=%d evaluated=%d",
                    len(batch),
                    len(batch_evaluations),
                )

            evaluations.extend(batch_evaluations)

        return evaluations


    async def _evaluate_batch(
        self,
        topics: list[TrendingTopic],
    ) -> list[TopicEvaluation]:

        topic_data = [
            {
                "topic": topic.topic,
                "category": topic.category,
                "summary": topic.summary,
                "keywords": topic.keywords,
            }
            for topic in topics
        ]

        system_prompt = self._build_system_prompt()

        user_prompt = json.dumps(
            {
                "topics": topic_data,
            },
            ensure_ascii=False,
        )

        response = await self.llm_client.generate(
            LlmRequest(
                messages=[
                    LlmMessage(
                        role="system",
                        content=system_prompt,
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
            )
        )

        data = json.loads(response.content)

        result = TopicEvaluationResult(**data)

        return result.evaluations

    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _resolve_batch_size(
        self,
        topic_count: int,
    ) -> int:
        if topic_count <= 20:
            return 20

        return 10
