from fastapi import APIRouter

# 상위 라우터가 하위 라우터를 조합하는 구조
from app.features.conversation_start.conversation_start_router import router as conversation_start_router
from app.features.trending.trending_router import router as trending_router

router = APIRouter(prefix="/ai/v1")

router.include_router(conversation_start_router)
router.include_router(trending_router)
