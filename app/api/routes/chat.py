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
        # Generate answer using Self-RAG or regular RAG
        if request.use_self_rag:
            answer = self_rag_service.self_rag_search(request.query)
        else:
            # Use regular RAG chain
            answer = rag_service.invoke(request.query)

        # Get reference sources
        search_results = rag_service.search(request.query, top_k=3)
        sources = [
            ChatSource(
                bvid=result.get("bvid", ""),
                title=result.get("title", ""),
                relevance=result.get("relevance_score", 0.0),
            )
            for result in search_results
        ]

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
