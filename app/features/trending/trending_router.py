from fastapi import APIRouter

from app.bootstrap import trending_service
from app.features.trending.trending_schemas import (
    TrendingRefreshResponse,
)

router = APIRouter(
    prefix="/trending",
    tags=["trending"],
)


@router.post(
    "/refresh",
    response_model=TrendingRefreshResponse,
)
async def refresh_trending_context() -> TrendingRefreshResponse:
    stored_count = await trending_service.refresh()

    return TrendingRefreshResponse(
        status="completed" if stored_count > 0 else "empty",
        stored_count=stored_count,
    )
