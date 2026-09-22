from app.shared.llm.client.base import LlmClient
from app.shared.llm.client.groq_client import GroqLlmClient
from app.core.config import Settings


def create_llm_client(settings: Settings) -> LlmClient:

    if settings.llm_provider == "groq":
        return GroqLlmClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

    elif settings.llm_provider == "openai":
        # return OpenAILlmClient(...)
        raise NotImplementedError("OpenAI provider is not implemented")

    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )