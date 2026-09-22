from fastapi.testclient import TestClient

from app.features.trending import trending_router
from app.main import app


client = TestClient(app)


class FakeTrendingService:
    async def refresh(self) -> int:
        return 2


def test_refresh_trending_context(monkeypatch):
    monkeypatch.setattr(
        trending_router,
        "trending_service",
        FakeTrendingService(),
    )

    response = client.post("/ai/v1/trending/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "stored_count": 2,
    }
