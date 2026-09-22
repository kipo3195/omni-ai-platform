from dataclasses import dataclass


@dataclass
class LlmMessage:
    role: str
    content: str


@dataclass
class LlmRequest:
    messages: list[LlmMessage]
    temperature: float = 0.7
    response_format: dict | None = None
    max_tokens: int | None = None
