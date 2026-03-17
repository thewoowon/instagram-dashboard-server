from fastapi import APIRouter
from app.api.v1.endpoints import accounts, ideas, drafts, generate, assets, analytics

api_router = APIRouter()

api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(ideas.router, prefix="/ideas", tags=["ideas"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(assets.router, prefix="/drafts", tags=["assets"])

api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
