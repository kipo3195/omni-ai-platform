from typing import Protocol

from app.features.returned_message_topics.returned_message_topics_state import (
    ReturnedMessageTopicsState,
)


class ReturnedMessageTopicsRunner(Protocol):
    async def ainvoke(
        self,
        input: ReturnedMessageTopicsState,
    ) -> dict:
        ...
