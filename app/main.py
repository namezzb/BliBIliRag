from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.videos import router as videos_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    active_settings.ensure_directories()

    application = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(videos_router)
    register_exception_handlers(application)
    return application


app = create_app()
