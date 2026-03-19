"""Tests for task management API routes."""
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
    settings = Settings(app_env="test")
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture
def task_queue():
    """Create task queue."""
    return TaskQueue()


class TestTaskRoutes:
    """Test task management API routes."""

    def test_create_task(self, client, task_queue):
        """Test creating a task."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.post(
                "/api/v1/tasks",
                json={
                    "task_type": "import_videos",
                    "metadata": {"folder_id": 123},
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "import_videos"
        assert data["status"] == "pending"
        assert data["task_id"] is not None

    def test_create_task_invalid_type(self, client, task_queue):
        """Test creating task with invalid type."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.post(
                "/api/v1/tasks",
                json={
                    "task_type": "invalid_type",
                },
            )

        assert response.status_code == 422  # Validation error

    def test_list_tasks_all(self, client, task_queue):
        """Test listing all tasks."""
        task_queue.enqueue(TaskType.IMPORT_VIDEOS)
        task_queue.enqueue(TaskType.INDEX_VIDEO)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["tasks"]) == 2

    def test_list_tasks_with_status_filter(self, client, task_queue):
        """Test listing tasks with status filter."""
        task_id1 = task_queue.enqueue(TaskType.IMPORT_VIDEOS)
        task_id2 = task_queue.enqueue(TaskType.INDEX_VIDEO)

        task_queue.update_task(task_id1, status=TaskStatus.COMPLETED)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get("/api/v1/tasks?status=completed")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["task_id"] == task_id1

    def test_list_tasks_with_pagination(self, client, task_queue):
        """Test listing tasks with pagination."""
        for _ in range(25):
            task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get("/api/v1/tasks?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["tasks"]) == 10
        assert data["skip"] == 0
        assert data["limit"] == 10

    def test_list_tasks_invalid_status(self, client, task_queue):
        """Test listing tasks with invalid status."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get("/api/v1/tasks?status=invalid")

        assert response.status_code == 422  # Validation error

    def test_get_task(self, client, task_queue):
        """Test getting a task."""
        task_id = task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["task_type"] == "import_videos"

    def test_get_nonexistent_task(self, client, task_queue):
        """Test getting nonexistent task."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get("/api/v1/tasks/nonexistent")

        assert response.status_code == 404

    def test_update_task_status(self, client, task_queue):
        """Test updating task status."""
        task_id = task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.patch(
                f"/api/v1/tasks/{task_id}",
                json={"status": "completed"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_update_task_progress(self, client, task_queue):
        """Test updating task progress."""
        task_id = task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.patch(
                f"/api/v1/tasks/{task_id}",
                json={
                    "progress": 50,
                    "completed": 5,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["progress"] == 50
        assert data["completed"] == 5

    def test_update_task_with_error(self, client, task_queue):
        """Test updating task with error."""
        task_id = task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.patch(
                f"/api/v1/tasks/{task_id}",
                json={
                    "status": "failed",
                    "error": "Connection timeout",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Connection timeout"

    def test_update_task_with_result(self, client, task_queue):
        """Test updating task with result."""
        task_id = task_queue.enqueue(TaskType.SEARCH)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.patch(
                f"/api/v1/tasks/{task_id}",
                json={
                    "status": "completed",
                    "result": {"count": 10, "items": []},
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["count"] == 10

    def test_update_nonexistent_task(self, client, task_queue):
        """Test updating nonexistent task."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.patch(
                "/api/v1/tasks/nonexistent",
                json={"status": "completed"},
            )

        assert response.status_code == 404

    def test_cancel_task(self, client, task_queue):
        """Test cancelling a task."""
        task_id = task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.delete(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_nonexistent_task(self, client, task_queue):
        """Test cancelling nonexistent task."""
        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.delete("/api/v1/tasks/nonexistent")

        assert response.status_code == 404

    def test_get_stats(self, client, task_queue):
        """Test getting queue statistics."""
        task_id1 = task_queue.enqueue(TaskType.IMPORT_VIDEOS)
        task_id2 = task_queue.enqueue(TaskType.INDEX_VIDEO)

        task_queue.dequeue()  # Move one to running
        task_queue.update_task(task_id2, status=TaskStatus.COMPLETED)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get("/api/v1/tasks/stats/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["running"] == 1
        assert data["completed"] == 1

    def test_task_response_format(self, client, task_queue):
        """Test task response format."""
        task_id = task_queue.enqueue(TaskType.IMPORT_VIDEOS)

        with patch("app.api.routes.tasks.get_task_queue", return_value=task_queue):
            response = client.get(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        assert "task_id" in data
        assert "task_type" in data
        assert "status" in data
        assert "progress" in data
        assert "total" in data
        assert "completed" in data
        assert "error" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "result" in data
