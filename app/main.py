from fastapi import FastAPI

from app.api.v1.router import (
    router as api_v1_router,
)
from app.core.logging_config import setup_logging

setup_logging()


app = FastAPI(
    title="Omni AI Platform",
)

app.include_router(
    api_v1_router
)

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }
