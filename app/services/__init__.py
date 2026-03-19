"""Application services package."""

from app.services.bilibili_auth import BilibiliAPIClient, BilibiliAuthError, BilibiliAuthService
from app.services.bilibili_content import BilibiliContentError, BilibiliContentService
from app.services.indexing import (
    DeterministicEmbeddingProvider,
    IndexingService,
    IndexingServiceError,
    LocalJsonVectorStore,
    ChromaDBVectorStore,
)
from app.services.rag_retrieval import (
    RAGRetrievalService,
    RAGRetrievalError,
    RAGChain,
    SimpleRetriever,
    MultiQueryRetriever,
)
from app.services.rag_routing import (
    LLMRoutingService,
    LLMRoutingError,
)
from app.services.rag_self_rag import (
    SelfRAGService,
    SelfRAGError,
)
from app.services.summary import SummaryService, SummaryServiceError
from app.services.subtitle import SubtitleService, clean_subtitle_text
from app.services.task_queue import TaskQueue, Task, TaskStatus, TaskType

__all__ = [
    "BilibiliAPIClient",
    "BilibiliAuthError",
    "BilibiliAuthService",
    "BilibiliContentService",
    "BilibiliContentError",
    "DeterministicEmbeddingProvider",
    "IndexingService",
    "IndexingServiceError",
    "LocalJsonVectorStore",
    "ChromaDBVectorStore",
    "RAGRetrievalService",
    "RAGRetrievalError",
    "RAGChain",
    "SimpleRetriever",
    "MultiQueryRetriever",
    "LLMRoutingService",
    "LLMRoutingError",
    "SelfRAGService",
    "SelfRAGError",
    "SummaryService",
    "SummaryServiceError",
    "SubtitleService",
    "clean_subtitle_text",
    "TaskQueue",
    "Task",
    "TaskStatus",
    "TaskType",
]
