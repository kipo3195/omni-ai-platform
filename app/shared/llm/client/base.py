from abc import ABC, abstractmethod

from app.shared.llm.model.request import LlmRequest
from app.shared.llm.model.response import LlmResponse


class LlmClient(ABC):

    @abstractmethod
    async def generate(
        self,
        request: LlmRequest,
    ) -> LlmResponse:
        pass