from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.core.config import Settings

router = APIRouter(tags=["system"])


@router.get("/")
async def root(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }


@router.get("/api/health")
async def health(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}

