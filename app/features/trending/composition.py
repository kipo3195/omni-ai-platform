from app.features.trending.enrichers.google_news_context_enricher import (
    GoogleNewsContextEnricher,
)
from app.features.trending.evaluators.llm_news_context_evaluator import (
    LlmNewsContextEvaluator,
)
from app.features.trending.evaluators.llm_topic_evaluator import LlmTopicEvaluator
from app.features.trending.generators.llm_base_question_generator import (
    LlmTrendingBaseQuestionGenerator,
)
from app.features.trending.policies.news_context_selection_policy import (
    NewsContextSelectionPolicy,
)
from app.features.trending.policies.trending_topic_selection_policy import (
    TrendingTopicSelectionPolicy,
)
from app.features.trending.providers.google_trends_provider import (
    GoogleTrendingProvider,
)
from app.features.trending.trending_repository import TrendingRepository
from app.features.trending.trending_service import TrendingService
from app.shared.llm.client.base import LlmClient


def create_trending_service(
    *,
    llm_client: LlmClient,
) -> TrendingService:
    return TrendingService(
        repository=TrendingRepository(),
        provider=GoogleTrendingProvider(limit=20),
        evaluator=LlmTopicEvaluator(llm_client=llm_client),
        context_enricher=GoogleNewsContextEnricher(),
        policy=TrendingTopicSelectionPolicy(),
        news_context_evaluator=LlmNewsContextEvaluator(
            llm_client=llm_client,
        ),
        news_context_selection_policy=NewsContextSelectionPolicy(),
        base_question_generator=LlmTrendingBaseQuestionGenerator(
            llm_client=llm_client,
            batch_size=5,
        ),
    )
