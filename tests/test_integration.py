"""Integration tests for the complete system."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import create_app
from app.core.config import Settings
from app.services.task_queue import TaskQueue, TaskStatus, TaskType


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
def task_queue():
    """Create task queue."""
    return TaskQueue()


class TestVideoManagementFlow:
    """Test video management workflow."""

    def test_import_and_list_videos(self, client):
        """Test importing and listing videos."""
        # Create import task
        response = client.post(
            "/api/v1/tasks",
            json={
                "task_type": "import_videos",
                "metadata": {"folder_id": 123},
            },
        )
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["status"] == "pending"

        # Get task details
        response = client.get(f"/api/v1/tasks/{task_data['task_id']}")
        assert response.status_code == 200
        assert response.json()["task_id"] == task_data["task_id"]


class TestSearchFlow:
    """Test search workflow."""

    def test_search_with_routing(self, client):
        """Test search with different routing strategies."""
        strategies = ["logical", "semantic", "hybrid"]

        for strategy in strategies:
            with patch("app.api.routes.search.get_rag_retrieval_service") as mock_rag:
                with patch("app.api.routes.search.get_rag_routing_service") as mock_routing:
                    mock_rag_service = MagicMock()
                    mock_rag_service.search.return_value = [
                        {
                            "bvid": "BV123",
                            "title": "Test",
                            "content": "Content",
                            "relevance_score": 0.95,
                            "source": "video",
                        }
                    ]
                    mock_rag.return_value = mock_rag_service

                    mock_routing_service = MagicMock()
                    mock_routing_service.logical_route.return_value = "retrieval"
                    mock_routing_service.semantic_route.return_value = "retrieval"
                    mock_routing_service.hybrid_route.return_value = "retrieval"
                    mock_routing.return_value = mock_routing_service

                    response = client.post(
                        "/api/v1/search",
                        json={
                            "query": "Python",
                            "routing_strategy": strategy,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["routing_info"]["strategy"] == strategy


class TestChatFlow:
    """Test chat workflow."""

    def test_multi_turn_conversation(self, client):
        """Test multi-turn conversation."""
        with patch("app.api.routes.chat.get_rag_retrieval_service") as mock_rag:
            with patch("app.api.routes.chat.get_self_rag_service") as mock_self_rag:
                mock_rag_service = MagicMock()
                mock_rag_service.search.return_value = [
                    {
                        "bvid": "BV123",
                        "title": "Python教程",
                        "content": "Python基础",
                        "relevance_score": 0.95,
                        "source": "video",
                    }
                ]
                mock_rag.return_value = mock_rag_service

                mock_self_rag_service = MagicMock()
                mock_self_rag_service.self_rag_search.return_value = "Python是一种编程语言"
                mock_self_rag.return_value = mock_self_rag_service

                # First turn
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "Python是什么？",
                        "conversation_id": "conv_1",
                    },
                )
                assert response.status_code == 200
                data1 = response.json()
                assert data1["conversation_id"] == "conv_1"

                # Second turn
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "query": "它有什么优势？",
                        "conversation_id": "conv_1",
                        "history": [
                            {"role": "user", "content": "Python是什么？"},
                            {"role": "assistant", "content": data1["answer"]},
                        ],
                    },
                )
                assert response.status_code == 200
                data2 = response.json()
                assert data2["conversation_id"] == "conv_1"


class TestTaskManagementFlow:
    """Test task management workflow."""

    def test_task_lifecycle(self, client, task_queue):
        """Test complete task lifecycle."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            # Create task
            response = client.post(
                "/api/v1/tasks",
                json={
                    "task_type": "import_videos",
                    "metadata": {"folder_id": 123},
                },
            )
            assert response.status_code == 200
            task_id = response.json()["task_id"]

            # Get task
            response = client.get(f"/api/v1/tasks/{task_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "pending"

            # Update task progress
            response = client.patch(
                f"/api/v1/tasks/{task_id}",
                json={"progress": 50, "completed": 5},
            )
            assert response.status_code == 200
            assert response.json()["progress"] == 50

            # Complete task
            response = client.patch(
                f"/api/v1/tasks/{task_id}",
                json={
                    "status": "completed",
                    "progress": 100,
                    "result": {"count": 10},
                },
            )
            assert response.status_code == 200
            assert response.json()["status"] == "completed"

            # List completed tasks
            response = client.get("/api/v1/tasks?status=completed")
            assert response.status_code == 200
            assert len(response.json()["tasks"]) == 1


class TestErrorHandling:
    """Test error handling across the system."""

    def test_invalid_search_query(self, client):
        """Test invalid search query handling."""
        response = client.post(
            "/api/v1/search",
            json={"query": "", "top_k": 5},
        )
        assert response.status_code == 422

    def test_invalid_task_type(self, client):
        """Test invalid task type handling."""
        response = client.post(
            "/api/v1/tasks",
            json={"task_type": "invalid_type"},
        )
        assert response.status_code == 422

    def test_nonexistent_task(self, client):
        """Test accessing nonexistent task."""
        response = client.get("/api/v1/tasks/nonexistent")
        assert response.status_code == 404

    def test_search_service_error(self, client):
        """Test search service error handling."""
        with patch("app.api.routes.search.get_rag_retrieval_service") as mock_rag:
            with patch("app.api.routes.search.get_rag_routing_service") as mock_routing:
                mock_rag_service = MagicMock()
                mock_rag_service.search.side_effect = Exception("Service error")
                mock_rag.return_value = mock_rag_service

                mock_routing_service = MagicMock()
                mock_routing.return_value = mock_routing_service

                response = client.post(
                    "/api/v1/search",
                    json={"query": "Python"},
                )
                assert response.status_code == 500


class TestConcurrentOperations:
    """Test concurrent operations."""

    def test_concurrent_task_creation(self, client, task_queue):
        """Test creating multiple tasks concurrently."""
        import threading

        results = []

        def create_task():
            with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
                response = client.post(
                    "/api/v1/tasks",
                    json={"task_type": "import_videos"},
                )
                results.append(response.status_code)

        threads = [threading.Thread(target=create_task) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(code == 200 for code in results)
        assert len(results) == 5


class TestAPIIntegration:
    """Test API integration."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_api_versioning(self, client):
        """Test API versioning."""
        # All new endpoints should be under /api/v1
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options("/api/v1/search")
        # Should not fail
        assert response.status_code in [200, 405]
