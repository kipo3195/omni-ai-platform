# 어떤 trend를 유지할 것인가
import logging

from app.features.trending.trending_repository import TrendingRepository
from app.features.trending.providers.provider import TrendingProvider
from app.features.trending.evaluators.base import TopicEvaluator
from app.features.trending.evaluators.base import NewsContextEvaluator
from app.features.trending.evaluators.base import TrendingBaseQuestionGenerator
from app.features.trending.enrichers.trending_context_enricher import TrendingContextEnricher
from app.features.trending.policies.trending_topic_selection_policy import TrendingTopicSelectionPolicy
from app.features.trending.policies.news_context_selection_policy import (
    NewsContextSelectionPolicy,
)

from app.features.trending.trending_models import (
    EvaluatedTrendingTopic,
    TrendingBaseQuestion,
)

logger = logging.getLogger(__name__)

class TrendingService:

    def __init__(
        self,
        repository: TrendingRepository,
        provider: TrendingProvider,
        evaluator: TopicEvaluator,
        context_enricher: TrendingContextEnricher,
        policy: TrendingTopicSelectionPolicy,
        news_context_evaluator: NewsContextEvaluator,
        news_context_selection_policy: NewsContextSelectionPolicy,
        base_question_generator: TrendingBaseQuestionGenerator,
    ):
        self.repository = repository
        self.provider = provider
        self.evaluator = evaluator
        self.context_enricher = context_enricher
        self.policy = policy
        self.news_context_evaluator = news_context_evaluator
        self.news_context_selection_policy = news_context_selection_policy
        self.base_question_generator = base_question_generator

    async def get_context(
        self,
        limit: int = 10,
        exclude_topics: list[str] | None = None,
    ):
        exclude_topics = exclude_topics or []

        topics = await self.repository.find_all()

        topics = [
            topic
            for topic in topics
            if topic.topic not in exclude_topics
        ]

        return topics[:limit]

    async def refresh(self) -> int:
        try:
            # topic 조회 
            topics = await self.provider.fetch()

            if not topics:
                logger.warning(
                    "trending provider returned empty topics"
                )
                return 0

            # LLM topic evaluate 
            evaluated_topics = await self.evaluator.evaluate(topics)

            if not evaluated_topics:
                logger.warning(
                    "topic evaluator returned empty evaluations"
                )
                return 0

            # 평가된 점수를 기준으로 필터
            selected_topics = self.policy.select_topics(
                topics=topics,
                evaluations=evaluated_topics,
            )

            # trend가 어떤 키워드를 갖는지 보강 
            enriched_topics = await self.context_enricher.enrich(selected_topics)

            if not enriched_topics:
                logger.warning("trending context enricher returned empty topics")
                return 0

            # news_items 기준 trend_context + 수치화 평가
            news_context_evaluations = await self.news_context_evaluator.evaluate(
                enriched_topics
            )

            if not news_context_evaluations:
                logger.warning("news context evaluator returned empty evaluations")
                return 0

            # 평가된 점수를 기준으로 필터
            selected_evaluated_topics = self.news_context_selection_policy.select(
                topics=enriched_topics,
                evaluations=news_context_evaluations,
            )
            
            if not selected_evaluated_topics:
                logger.warning("no trending topics passed news context evaluation")
                return 0

            # 통과한 topic에 대해서만 base question 생성(batch)
            base_questions = await self.base_question_generator.generate(
                selected_evaluated_topics
            )

            # 생성한 질문 목록을 최종 저장할 topic 목록에 붙이는 매칭 로직
            selected_evaluated_topics = self._attach_base_questions(
                topics=selected_evaluated_topics,
                base_questions=base_questions,
            )

            # repository 저장
            await self.repository.replace(selected_evaluated_topics)

            logger.info(
                "trending topics refreshed "
                "fetched=%d topic_evaluated=%d topic_selected=%d "
                "news_enriched=%d news_context_evaluated=%d "
                "base_question_generated=%d stored=%d",
                len(topics),
                len(evaluated_topics),
                len(selected_topics),
                len(enriched_topics),
                len(news_context_evaluations),
                len(base_questions),
                len(selected_evaluated_topics),
            )

            for topic in selected_evaluated_topics:
                logger.info(
                    "stored trending topic "
                    "topic=%s score=%.3f "
                    "generality=%.2f "
                    "lightness=%.2f "
                    "conversationality=%.2f "
                    "sensitivity=%.2f "
                    "smalltalk_fit=%.2f "
                    "specificity=%.2f "
                    "trend_context=%s "
                    "base_question=%s",
                    topic.topic,
                    topic.score,
                    topic.generality,
                    topic.lightness,
                    topic.conversationality,
                    topic.sensitivity,
                    topic.smalltalk_fit,
                    topic.specificity,
                    topic.trend_context,
                    topic.base_question,
                )

            return len(selected_evaluated_topics)

        except Exception:
            logger.exception(
                "failed to refresh trending topics"
            )
            return 0

    def _attach_base_questions(
        self,
        topics: list[EvaluatedTrendingTopic],
        base_questions: list[TrendingBaseQuestion],
    ) -> list[EvaluatedTrendingTopic]:
        question_map = {
            item.topic: item.question
            for item in base_questions
        }

        return [
            topic.model_copy(
                update={
                    "base_question": question_map.get(topic.topic),
                }
            )
            for topic in topics
        ]
