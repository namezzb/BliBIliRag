from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories import SessionStore
from app.services import BilibiliAPIClient, BilibiliAuthService


def get_app_settings() -> Settings:
    return get_settings()


def get_session_store(
    settings: Settings = Depends(get_app_settings),
) -> SessionStore:
    return SessionStore(settings.bilibili_session_path)


def get_bilibili_auth_service(
    settings: Settings = Depends(get_app_settings),
    session_store: SessionStore = Depends(get_session_store),
) -> BilibiliAuthService:
    return BilibiliAuthService(
        settings=settings,
        api_client=BilibiliAPIClient(),
        session_store=session_store,
    )
