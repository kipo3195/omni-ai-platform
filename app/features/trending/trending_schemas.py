from pydantic import BaseModel


class TrendingRefreshResponse(BaseModel):
    status: str
    stored_count: int
