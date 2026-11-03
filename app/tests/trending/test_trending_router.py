from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.trending.trending_router import create_trending_router


class FakeTrendingService:
    async def refresh(self) -> int:
        return 2


def test_refresh_trending_context():
    app = FastAPI()
    app.include_router(
        create_trending_router(FakeTrendingService()),
        prefix="/ai/v1",
    )
    client = TestClient(app)

    response = client.post("/ai/v1/trending/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "stored_count": 2,
    }
