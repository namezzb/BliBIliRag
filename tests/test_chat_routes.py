"""Tests for chat API routes."""
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
    service.invoke.return_value = "Python是一种编程语言"
    service.search.return_value = [
        {
            "bvid": "BV123",
            "title": "Python教程",
            "content": "Python基础",
            "relevance_score": 0.95,
            "source": "video",
        }
    ]
    return service


@pytest.fixture
def mock_self_rag_service():
    """Create mock Self-RAG service."""
    service = MagicMock()
    service.self_rag_search.return_value = "Python是一种高级编程语言，具有简洁的语法"
    return service


class TestChatRoutes:
    """Test chat API routes."""

    def test_chat_basic(self, client, mock_rag_service, mock_self_rag_service):
        """Test basic chat."""
        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python是什么？",
                        "conversation_id": "conv_1",
                        "use_self_rag": True,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Python是什么？"
        assert data["conversation_id"] == "conv_1"
        assert len(data["answer"]) > 0
        assert len(data["sources"]) > 0

    def test_chat_with_self_rag_enabled(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat with Self-RAG enabled."""
        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python有什么优势？",
                        "use_self_rag": True,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["use_self_rag"] is True
        mock_self_rag_service.self_rag_search.assert_called_once()

    def test_chat_with_self_rag_disabled(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat with Self-RAG disabled."""
        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python有什么优势？",
                        "use_self_rag": False,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["use_self_rag"] is False
        mock_rag_service.invoke.assert_called_once()

    def test_chat_with_history(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat with conversation history."""
        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "继续说",
                        "conversation_id": "conv_1",
                        "history": [
                            {"role": "user", "content": "Python是什么？"},
                            {"role": "assistant", "content": "Python是一种编程语言"},
                        ],
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "继续说"

    def test_chat_empty_query(self, client):
        """Test chat with empty query."""
        response = client.post(
            "/api/v1/chat",
            json={
                "query": "",
                "conversation_id": "conv_1",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_chat_query_too_long(self, client):
        """Test chat with query too long."""
        response = client.post(
            "/api/v1/chat",
            json={
                "query": "a" * 2001,
                "conversation_id": "conv_1",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_chat_invalid_role(self, client):
        """Test chat with invalid message role."""
        response = client.post(
            "/api/v1/chat",
            json={
                "query": "Python是什么？",
                "history": [
                    {"role": "invalid", "content": "test"},
                ],
            },
        )

        assert response.status_code == 422  # Validation error

    def test_chat_multiple_sources(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat with multiple sources."""
        mock_rag_service.search.return_value = [
            {
                "bvid": "BV123",
                "title": "Python基础",
                "content": "基础教程",
                "relevance_score": 0.95,
                "source": "video",
            },
            {
                "bvid": "BV456",
                "title": "Python进阶",
                "content": "进阶教程",
                "relevance_score": 0.85,
                "source": "video",
            },
            {
                "bvid": "BV789",
                "title": "Python项目",
                "content": "项目实战",
                "relevance_score": 0.75,
                "source": "video",
            },
        ]

        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python教程",
                        "conversation_id": "conv_1",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 3

    def test_chat_error_handling(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat error handling."""
        mock_self_rag_service.self_rag_search.side_effect = Exception("RAG failed")

        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python是什么？",
                        "use_self_rag": True,
                    },
                )

        assert response.status_code == 500
        data = response.json()
        assert "Chat failed" in data["detail"]

    def test_chat_default_conversation_id(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat with default conversation ID."""
        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python是什么？",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "default"

    def test_chat_default_use_self_rag(self, client, mock_rag_service, mock_self_rag_service):
        """Test chat with default use_self_rag."""
        with patch("app.api.routes.chat.get_rag_retrieval_service", return_value=mock_rag_service):
            with patch("app.api.routes.chat.get_self_rag_service", return_value=mock_self_rag_service):
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python是什么？",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["use_self_rag"] is True
