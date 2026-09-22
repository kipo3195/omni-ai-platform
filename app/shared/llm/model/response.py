from dataclasses import dataclass
from typing import Any


@dataclass
class LlmResponse:
    content: str
    model: str | None = None
    usage: Any | None = None