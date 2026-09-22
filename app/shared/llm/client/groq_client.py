from groq import AsyncGroq

from app.shared.llm.client.base import LlmClient
from app.shared.llm.model.request import LlmRequest
from app.shared.llm.model.response import LlmResponse


class GroqLlmClient(LlmClient):

    def __init__(
        self,
        api_key: str,
        model: str,
    ):
        self.client = AsyncGroq(api_key=api_key)
        self.model = model

    async def generate(
        self,
        request: LlmRequest
    ) -> LlmResponse:
        completion_params = {
            "model": self.model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "temperature": request.temperature,
        }

        if request.response_format is not None:
            completion_params["response_format"] = request.response_format

        if request.max_tokens is not None:
            completion_params["max_tokens"] = request.max_tokens

        response = await self.client.chat.completions.create(**completion_params)

        return LlmResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage=response.usage,
        )
