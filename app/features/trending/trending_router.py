from fastapi import APIRouter

from app.features.trending.ports import TrendingRefresher
from app.features.trending.trending_schemas import (
    TrendingRefreshResponse,
)


def create_trending_router(
    service: TrendingRefresher,
) -> APIRouter:
    router = APIRouter(
        prefix="/trending",
        tags=["trending"],
    )

    @router.post(
        "/refresh",
        response_model=TrendingRefreshResponse,
    )
    async def refresh_trending_context() -> TrendingRefreshResponse:
        stored_count = await service.refresh()

        return TrendingRefreshResponse(
            status="completed" if stored_count > 0 else "empty",
            stored_count=stored_count,
        )

    return router
