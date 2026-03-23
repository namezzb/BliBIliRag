"""Chat API routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import (
    get_rag_retrieval_service,
    get_self_rag_service,
)
from app.services.rag_retrieval import RAGRetrievalService
from app.services.rag_self_rag import SelfRAGService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str = Field(default="default")
    use_self_rag: bool = Field(default=True)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatSource(BaseModel):
    """Chat source reference."""
    bvid: str
    title: str
    relevance: float


class ChatResponse(BaseModel):
    """Chat response model."""
    conversation_id: str
    query: str
    answer: str
    sources: list[ChatSource]
    use_self_rag: bool


def _normalize_sources(search_results: list[dict]) -> list[ChatSource]:
    sources: list[ChatSource] = []
    for result in search_results:
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        bvid = str(result.get("bvid") or metadata.get("bvid") or "")
        title = str(result.get("title") or metadata.get("title") or "")
        relevance = float(result.get("relevance_score") or result.get("score") or 0.0)
        sources.append(
            ChatSource(
                bvid=bvid,
                title=title,
                relevance=relevance,
            )
        )
    return sources


def _build_fallback_answer(query: str, search_results: list[dict]) -> str:
    if not search_results:
        return f"暂时没有检索到与“{query}”相关的内容。请先导入并索引收藏视频后再试。"

    lines = [f"已根据你的问题“{query}”检索到以下内容："]
    for idx, result in enumerate(search_results[:3], start=1):
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        title = str(result.get("title") or metadata.get("title") or "未命名视频")
        content = str(result.get("content") or result.get("document") or "")
        snippet = content[:120] if content else "暂无文本摘要"
        lines.append(f"{idx}. {title}：{snippet}")
    lines.append("当前未配置可用大模型，以上为检索结果摘要。")
    return "\n".join(lines)


def _is_llm_unavailable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "llm_not_configured" in message
        or "unsupported type: <class 'nonetype'>" in message
        or "none type" in message
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_service: RAGRetrievalService = Depends(get_rag_retrieval_service),
    self_rag_service: SelfRAGService = Depends(get_self_rag_service),
) -> ChatResponse:
    """Execute chat with RAG support.

    Args:
        request: Chat request
        rag_service: RAG retrieval service
        self_rag_service: Self-RAG service

    Returns:
        Chat response with answer and sources
    """
    try:
        search_results = rag_service.search(request.query, top_k=3)

        # Generate answer using Self-RAG or regular RAG
        if request.use_self_rag:
            try:
                answer = self_rag_service.self_rag_search(request.query)
            except Exception as exc:
                if not _is_llm_unavailable_error(exc):
                    raise
                answer = _build_fallback_answer(request.query, search_results)
        else:
            try:
                answer = rag_service.invoke(request.query)
            except Exception as exc:
                if not _is_llm_unavailable_error(exc):
                    raise
                answer = _build_fallback_answer(request.query, search_results)

        sources = _normalize_sources(search_results)

        return ChatResponse(
            conversation_id=request.conversation_id,
            query=request.query,
            answer=answer,
            sources=sources,
            use_self_rag=request.use_self_rag,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
) -> dict:
    """Get conversation history.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation history
    """
    # TODO: Implement conversation history from database
    return {
        "conversation_id": conversation_id,
        "messages": [],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
) -> dict:
    """Delete conversation.

    Args:
        conversation_id: Conversation ID

    Returns:
        Deletion status
    """
    # TODO: Implement conversation deletion
    return {
        "status": "deleted",
        "conversation_id": conversation_id,
    }
