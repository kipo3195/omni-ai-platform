import json
import logging
from json import JSONDecodeError

from pydantic import ValidationError

from app.features.trending.evaluators.base import TrendingBaseQuestionGenerator
from app.features.trending.prompts.base_question_prompt import SYSTEM_PROMPT
from app.features.trending.trending_models import (
    EvaluatedTrendingTopic,
    TrendingBaseQuestion,
    TrendingBaseQuestionResult,
)
from app.shared.llm.client.base import LlmClient
from app.shared.llm.model.request import LlmMessage, LlmRequest

logger = logging.getLogger(__name__)


class LlmTrendingBaseQuestionGenerator(TrendingBaseQuestionGenerator):

    def __init__(
        self,
        llm_client: LlmClient,
        batch_size: int = 5,
    ):
        self.llm_client = llm_client
        self.batch_size = batch_size

    async def generate(
        self,
        topics: list[EvaluatedTrendingTopic],
    ) -> list[TrendingBaseQuestion]:
        if not topics:
            return []

        questions: list[TrendingBaseQuestion] = []

        for i in range(0, len(topics), self.batch_size):
            batch = topics[i:i + self.batch_size]
            batch_questions = await self._generate_batch(batch)

            if len(batch_questions) != len(batch):
                logger.warning(
                    "base question count mismatch requested=%d generated=%d",
                    len(batch),
                    len(batch_questions),
                )

            questions.extend(batch_questions)

        return questions

    async def _generate_batch(
        self,
        topics: list[EvaluatedTrendingTopic],
    ) -> list[TrendingBaseQuestion]:
        user_prompt = json.dumps(
            {
                "topics": [
                    self._to_prompt_item(topic)
                    for topic in topics
                ],
            },
            ensure_ascii=False,
        )

        system_prompt = self._build_system_prompt()
      
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
                temperature=0.7,
                response_format={
                    "type": "json_object",
                },
            )
        )

        try:
            data = self._decode_json_content(response.content)
            result = TrendingBaseQuestionResult(**data)
        except (JSONDecodeError, ValidationError, ValueError):
            logger.exception(
                "failed to parse base question response "
                "topics=%s raw_response=%r",
                [topic.topic for topic in topics],
                response.content[:2000],
            )
            return []

        topic_names = {topic.topic for topic in topics}
        questions = [
            question
            for question in result.questions
            if question.topic in topic_names and question.question.strip()
        ]

        for question in questions:
            logger.info(
                "trending base question generated topic=%s question=%s",
                question.topic,
                question.question,
            )

        return questions

    def _to_prompt_item(
        self,
        topic: EvaluatedTrendingTopic,
    ) -> dict:
        return {
            "topic": topic.topic,
            "category": topic.category,
            "summary": topic.summary,
            "keywords": topic.keywords,
            "trend_context": topic.trend_context,
            "score": topic.score,
        }
    
    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _decode_json_content(
        self,
        content: str,
    ):
        stripped = content.strip()

        if not stripped:
            raise ValueError("LLM response was empty")

        try:
            return json.loads(stripped)
        except JSONDecodeError:
            decoder = json.JSONDecoder()

            for index, char in enumerate(stripped):
                if char not in "{[":
                    continue

                try:
                    data, _ = decoder.raw_decode(stripped[index:])
                    return data
                except JSONDecodeError:
                    continue

        raise ValueError("LLM response did not contain JSON")
