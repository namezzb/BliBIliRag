from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories import Database, SessionStore, SubtitleRepository, SummaryRepository, VideoRepository
from app.services import (
    BilibiliAPIClient,
    BilibiliAuthService,
    BilibiliContentService,
    SubtitleService,
    RAGRetrievalService,
    LLMRoutingService,
    SelfRAGService,
)
from app.services.summary import DashScopeLLMProvider, SummaryService
from app.services.indexing import IndexingService, DashScopeEmbeddingProvider
from app.services.task_queue import TaskQueue


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


def get_summary_repository(
    database: Database = Depends(get_database),
) -> SummaryRepository:
    return SummaryRepository(database)


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


def get_summary_service(
    settings: Settings = Depends(get_app_settings),
    video_repository: VideoRepository = Depends(get_video_repository),
    subtitle_repository: SubtitleRepository = Depends(get_subtitle_repository),
    summary_repository: SummaryRepository = Depends(get_summary_repository),
) -> SummaryService:
    llm_provider = None
    if settings.dashscope_api_key:
        llm_provider = DashScopeLLMProvider(
            api_key=settings.dashscope_api_key,
            model=settings.dashscope_model
        )
    return SummaryService(
        video_repository=video_repository,
        subtitle_repository=subtitle_repository,
        summary_repository=summary_repository,
        llm_provider=llm_provider,
    )


def get_indexing_service(
    settings: Settings = Depends(get_app_settings),
    video_repository: VideoRepository = Depends(get_video_repository),
    summary_repository: SummaryRepository = Depends(get_summary_repository),
) -> IndexingService:
    embedding_provider = None
    if settings.dashscope_api_key:
        embedding_provider = DashScopeEmbeddingProvider(
            api_key=settings.dashscope_api_key,
            model=settings.dashscope_embedding_model,
        )
    return IndexingService(
        settings=settings,
        video_repository=video_repository,
        summary_repository=summary_repository,
        embedding_provider=embedding_provider,
    )


def get_rag_retrieval_service(
    settings: Settings = Depends(get_app_settings),
    indexing_service: IndexingService = Depends(get_indexing_service),
) -> RAGRetrievalService:
    """获取 RAG 检索服务"""
    from app.services.rag_retrieval import RAGRetrievalService
    from app.services.summary import DashScopeLLMProvider

    # 获取向量存储
    vector_store = indexing_service.vector_store

    # 获取 LLM
    llm = None
    if settings.dashscope_api_key:
        llm_provider = DashScopeLLMProvider(
            api_key=settings.dashscope_api_key,
            model=settings.dashscope_model
        )
        # 创建 LangChain LLM 包装器
        from langchain_community.llms import OpenAI
        llm = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=settings.dashscope_model,
        )

    # 获取 embedding provider
    embedding_provider = indexing_service.embedding_provider

    return RAGRetrievalService(
        vector_store=vector_store,
        llm=llm,
        embedding_provider=embedding_provider,
        cohere_api_key=settings.cohere_api_key if hasattr(settings, 'cohere_api_key') else None,
    )


def get_rag_routing_service(
    settings: Settings = Depends(get_app_settings),
    indexing_service: IndexingService = Depends(get_indexing_service),
) -> LLMRoutingService:
    """获取 LLM 路由服务"""
    from app.services.rag_routing import LLMRoutingService
    from app.services.summary import DashScopeLLMProvider

    # 获取 LLM
    llm = None
    if settings.dashscope_api_key:
        from langchain_community.llms import OpenAI
        llm = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=settings.dashscope_model,
        )

    # 获取 embedding provider
    embedding_provider = indexing_service.embedding_provider

    return LLMRoutingService(
        llm=llm,
        embedding_provider=embedding_provider,
    )


def get_self_rag_service(
    settings: Settings = Depends(get_app_settings),
    rag_retrieval: RAGRetrievalService = Depends(get_rag_retrieval_service),
) -> SelfRAGService:
    """获取 Self-RAG 服务"""
    from app.services.rag_self_rag import SelfRAGService

    # 获取 LLM
    llm = None
    if settings.dashscope_api_key:
        from langchain_community.llms import OpenAI
        llm = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=settings.dashscope_model,
        )

    return SelfRAGService(
        rag_retrieval=rag_retrieval,
        llm=llm,
    )


@lru_cache
def _get_cached_task_queue() -> TaskQueue:
    """Get cached task queue instance."""
    return TaskQueue()


def get_task_queue() -> TaskQueue:
    """Get task queue dependency."""
    return _get_cached_task_queue()
