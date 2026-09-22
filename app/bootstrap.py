from app.core.config import settings
from app.features.trending.trending_repository import TrendingRepository
from app.features.trending.trending_service import TrendingService
from app.features.trending.providers.google_trends_provider import GoogleTrendingProvider
from app.features.trending.evaluators.llm_topic_evaluator import LlmTopicEvaluator
from app.features.trending.enrichers.google_news_context_enricher import GoogleNewsContextEnricher
from app.features.trending.policies.trending_topic_selection_policy import TrendingTopicSelectionPolicy
from app.features.trending.evaluators.llm_news_context_evaluator import LlmNewsContextEvaluator
from app.features.trending.generators.llm_base_question_generator import (
    LlmTrendingBaseQuestionGenerator,
)
from app.features.trending.policies.news_context_selection_policy import NewsContextSelectionPolicy
from app.shared.llm.factory import create_llm_client
from app.features.conversation_start.conversation_start_graph import (
    create_conversation_start_graph,
)

# LLM Client 생성
llm_client = create_llm_client(settings)

# repository
trending_repository = TrendingRepository()

# provider
trending_provider = GoogleTrendingProvider(
    limit=20,
)

# trending evaluator
topic_evaluator = LlmTopicEvaluator(
    llm_client=llm_client,
)

# Google News enricher
context_enricher = GoogleNewsContextEnricher()

# topic select policy
topic_select_policy = TrendingTopicSelectionPolicy()

# news context evaluator
news_context_evaluator = LlmNewsContextEvaluator(
    llm_client=llm_client,
)

# news context selection policy
news_context_selection_policy = NewsContextSelectionPolicy()

# base question generator
base_question_generator = LlmTrendingBaseQuestionGenerator(
    llm_client=llm_client,
    batch_size=5,
)

# service
trending_service = TrendingService(
    repository=trending_repository,
    provider=trending_provider,
    evaluator=topic_evaluator,
    context_enricher=context_enricher,
    policy=topic_select_policy,
    news_context_evaluator=news_context_evaluator,
    news_context_selection_policy=news_context_selection_policy,
    base_question_generator=base_question_generator,
)

conversation_start_graph = create_conversation_start_graph(
    trending_service=trending_service,
)
