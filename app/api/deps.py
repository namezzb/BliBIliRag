from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories import Database, SessionStore, SubtitleRepository, VideoRepository
from app.services import (
    BilibiliAPIClient,
    BilibiliAuthService,
    BilibiliContentService,
    SubtitleService,
)


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


@lru_cache
def _get_cached_database(db_path: str) -> Database:
    database = Database(db_path)
    database.init_schema()
    return database


def get_database(settings: Settings = Depends(get_app_settings)) -> Database:
    return _get_cached_database(str(settings.sqlite_path))


def get_video_repository(
    database: Database = Depends(get_database),
) -> VideoRepository:
    return VideoRepository(database)


def get_subtitle_repository(
    database: Database = Depends(get_database),
) -> SubtitleRepository:
    return SubtitleRepository(database)


def get_bilibili_content_service(
    settings: Settings = Depends(get_app_settings),
    session_store: SessionStore = Depends(get_session_store),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> BilibiliContentService:
    return BilibiliContentService(
        settings=settings,
        api_client=BilibiliAPIClient(),
        session_store=session_store,
        video_repository=video_repository,
    )


def get_subtitle_service(
    settings: Settings = Depends(get_app_settings),
    session_store: SessionStore = Depends(get_session_store),
    subtitle_repository: SubtitleRepository = Depends(get_subtitle_repository),
) -> SubtitleService:
    return SubtitleService(
        settings=settings,
        api_client=BilibiliAPIClient(),
        session_store=session_store,
        subtitle_repository=subtitle_repository,
    )
