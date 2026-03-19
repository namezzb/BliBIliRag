"""Tests for search API routes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import create_app
from app.core.config import Settings


@pytest.fixture
def client():
    """Create test client."""
    settings = Settings(
        app_env="test",
        dashscope_api_key="test-key",
    )
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture
def mock_rag_service():
    """Create mock RAG service."""
    service = MagicMock()
    service.search.return_value = [
        {
            "bvid": "BV123",
            "title": "Test Video",
            "content": "Test content",
            "relevance_score": 0.95,
            "source": "video",
        }
    ]
    return service


@pytest.fixture
def mock_routing_service():
    """Create mock routing service."""
    service = MagicMock()
    service.logical_route.return_value = "retrieval"
    service.semantic_route.return_value = "retrieval"
    service.hybrid_route.return_value = "retrieval"
    return service


class TestSearchRoutes:
    """Test search API routes."""

    def test_search_basic(self, client, mock_rag_service, mock_routing_service):
        """Test basic search."""
        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={
                        "query": "Python编程",
                        "top_k": 5,
                        "routing_strategy": "hybrid",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Python编程"
        assert len(data["results"]) == 1
        assert data["results"][0]["bvid"] == "BV123"
        assert data["total_results"] == 1

    def test_search_with_logical_routing(self, client, mock_rag_service, mock_routing_service):
        """Test search with logical routing."""
        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={
                        "query": "什么是Python",
                        "top_k": 5,
                        "routing_strategy": "logical",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["routing_info"]["strategy"] == "logical"
        mock_routing_service.logical_route.assert_called_once()

    def test_search_with_semantic_routing(self, client, mock_rag_service, mock_routing_service):
        """Test search with semantic routing."""
        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={
                        "query": "Python编程",
                        "routing_strategy": "semantic",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["routing_info"]["strategy"] == "semantic"
        mock_routing_service.semantic_route.assert_called_once()

    def test_search_with_top_k(self, client, mock_rag_service, mock_routing_service):
        """Test search with custom top_k."""
        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={
                        "query": "Python",
                        "top_k": 10,
                    },
                )

        assert response.status_code == 200
        mock_rag_service.search.assert_called_with("Python", top_k=10)

    def test_search_empty_query(self, client):
        """Test search with empty query."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "",
                "top_k": 5,
            },
        )

        assert response.status_code == 422  # Validation error

    def test_search_query_too_long(self, client):
        """Test search with query too long."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "a" * 501,
                "top_k": 5,
            },
        )

        assert response.status_code == 422  # Validation error

    def test_search_invalid_top_k(self, client):
        """Test search with invalid top_k."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "Python",
                "top_k": 0,
            },
        )

        assert response.status_code == 422  # Validation error

    def test_search_invalid_routing_strategy(self, client):
        """Test search with invalid routing strategy."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "Python",
                "routing_strategy": "invalid",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_search_multiple_results(self, client, mock_rag_service, mock_routing_service):
        """Test search with multiple results."""
        mock_rag_service.search.return_value = [
            {
                "bvid": "BV123",
                "title": "Video 1",
                "content": "Content 1",
                "relevance_score": 0.95,
                "source": "video",
            },
            {
                "bvid": "BV456",
                "title": "Video 2",
                "content": "Content 2",
                "relevance_score": 0.85,
                "source": "video",
            },
        ]

        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={
                        "query": "Python",
                        "top_k": 5,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["total_results"] == 2

    def test_search_content_truncation(self, client, mock_rag_service, mock_routing_service):
        """Test that search results content is truncated."""
        long_content = "a" * 500
        mock_rag_service.search.return_value = [
            {
                "bvid": "BV123",
                "title": "Video",
                "content": long_content,
                "relevance_score": 0.95,
                "source": "video",
            }
        ]

        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={"query": "Python"},
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"][0]["content"]) == 200

    def test_search_error_handling(self, client, mock_rag_service, mock_routing_service):
        """Test search error handling."""
        mock_rag_service.search.side_effect = Exception("Search failed")

        with patch("app.api.routes.search.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.search.get_rag_routing_service", return_value=mock_routing_service):
                response = client.post(
                    "/api/v1/search",
                    json={"query": "Python"},
                )

        assert response.status_code == 500
        data = response.json()
        assert "Search failed" in data["detail"]
