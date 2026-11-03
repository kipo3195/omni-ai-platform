from typing import Protocol


class TrendingRefresher(Protocol):
    async def refresh(self) -> int:
        ...
