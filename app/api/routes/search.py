"""Search API routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import (
    get_rag_retrieval_service,
    get_rag_routing_service,
)
from app.services.rag_retrieval import RAGRetrievalService
from app.services.rag_routing import LLMRoutingService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=50)
    routing_strategy: str = Field(default="hybrid", pattern="^(logical|semantic|hybrid|direct)$")


class SearchResult(BaseModel):
    """Search result model."""
    bvid: str
    title: str
    content: str
    relevance_score: float
    source: str


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    results: list[SearchResult]
    routing_info: dict
    total_results: int


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    rag_service: RAGRetrievalService = Depends(get_rag_retrieval_service),
    routing_service: LLMRoutingService = Depends(get_rag_routing_service),
) -> SearchResponse:
    """Execute intelligent search.

    Args:
        request: Search request
        rag_service: RAG retrieval service
        routing_service: LLM routing service

    Returns:
        Search response with results
    """
    try:
        # Determine routing strategy
        if request.routing_strategy == "logical":
            route = routing_service.logical_route(request.query)
        elif request.routing_strategy == "semantic":
            route = routing_service.semantic_route(request.query)
        elif request.routing_strategy == "hybrid":
            route = routing_service.hybrid_route(request.query)
        else:
            route = "direct"

        # Execute search
        results = rag_service.search(request.query, top_k=request.top_k)

        # Format results
        formatted_results = [
            SearchResult(
                bvid=result.get("bvid", ""),
                title=result.get("title", ""),
                content=result.get("content", "")[:200],  # Truncate content
                relevance_score=result.get("relevance_score", 0.0),
                source=result.get("source", "video"),
            )
            for result in results
        ]

        return SearchResponse(
            query=request.query,
            results=formatted_results,
            routing_info={
                "strategy": request.routing_strategy,
                "route": route,
            },
            total_results=len(formatted_results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/history")
async def get_search_history(
    limit: int = Query(default=10, ge=1, le=100),
) -> dict:
    """Get search history.

    Args:
        limit: Maximum number of history items

    Returns:
        Search history
    """
    # TODO: Implement search history from database
    return {"history": []}
