"""Tests for task queue system."""
from __future__ import annotations

import time
import pytest

from app.services.task_queue import Task, TaskQueue, TaskStatus, TaskType


class TestTaskQueue:
    """Test task queue functionality."""

    def test_enqueue_task(self) -> None:
        """Test enqueueing a task."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS, {"folder_id": 123})

        assert task_id is not None
        task = queue.get_task(task_id)
        assert task is not None
        assert task.task_id == task_id
        assert task.task_type == TaskType.IMPORT_VIDEOS
        assert task.status == TaskStatus.PENDING
        assert task.metadata == {"folder_id": 123}

    def test_dequeue_task(self) -> None:
        """Test dequeueing a task."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.INDEX_VIDEO, {"bvid": "BV123"})

        task = queue.dequeue()
        assert task is not None
        assert task.task_id == task_id
        assert task.status == TaskStatus.RUNNING

    def test_dequeue_empty_queue(self) -> None:
        """Test dequeueing from empty queue."""
        queue = TaskQueue()
        task = queue.dequeue()
        assert task is None

    def test_get_task(self) -> None:
        """Test getting task by ID."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.GENERATE_SUMMARY)

        task = queue.get_task(task_id)
        assert task is not None
        assert task.task_id == task_id

    def test_get_nonexistent_task(self) -> None:
        """Test getting nonexistent task."""
        queue = TaskQueue()
        task = queue.get_task("nonexistent")
        assert task is None

    def test_update_task_status(self) -> None:
        """Test updating task status."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)

        updated = queue.update_task(task_id, status=TaskStatus.COMPLETED)
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED

    def test_update_task_progress(self) -> None:
        """Test updating task progress."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)

        updated = queue.update_task(task_id, progress=50, completed=5, total=10)
        assert updated is not None
        assert updated.progress == 50
        assert updated.completed == 5
        assert updated.total == 10

    def test_update_task_with_result(self) -> None:
        """Test updating task with result."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.SEARCH)

        result = {"count": 10, "items": []}
        updated = queue.update_task(task_id, result=result)
        assert updated is not None
        assert updated.result == result

    def test_update_task_with_error(self) -> None:
        """Test updating task with error."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)

        updated = queue.update_task(task_id, status=TaskStatus.FAILED, error="Connection timeout")
        assert updated is not None
        assert updated.status == TaskStatus.FAILED
        assert updated.error == "Connection timeout"

    def test_list_tasks_all(self) -> None:
        """Test listing all tasks."""
        queue = TaskQueue()
        queue.enqueue(TaskType.IMPORT_VIDEOS)
        queue.enqueue(TaskType.INDEX_VIDEO)
        queue.enqueue(TaskType.GENERATE_SUMMARY)

        tasks, total = queue.list_tasks()
        assert total == 3
        assert len(tasks) == 3

    def test_list_tasks_with_status_filter(self) -> None:
        """Test listing tasks with status filter."""
        queue = TaskQueue()
        task_id1 = queue.enqueue(TaskType.IMPORT_VIDEOS)
        task_id2 = queue.enqueue(TaskType.INDEX_VIDEO)

        queue.update_task(task_id1, status=TaskStatus.COMPLETED)

        tasks, total = queue.list_tasks(status=TaskStatus.COMPLETED)
        assert total == 1
        assert tasks[0].task_id == task_id1

    def test_list_tasks_with_pagination(self) -> None:
        """Test listing tasks with pagination."""
        queue = TaskQueue()
        for _ in range(25):
            queue.enqueue(TaskType.IMPORT_VIDEOS)

        tasks, total = queue.list_tasks(skip=0, limit=10)
        assert total == 25
        assert len(tasks) == 10

        tasks, total = queue.list_tasks(skip=10, limit=10)
        assert len(tasks) == 10

        tasks, total = queue.list_tasks(skip=20, limit=10)
        assert len(tasks) == 5

    def test_cancel_task_pending(self) -> None:
        """Test cancelling a pending task."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)

        cancelled = queue.cancel_task(task_id)
        assert cancelled is not None
        assert cancelled.status == TaskStatus.CANCELLED

    def test_cancel_task_running(self) -> None:
        """Test cancelling a running task."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)
        queue.dequeue()  # Move to running

        cancelled = queue.cancel_task(task_id)
        assert cancelled is not None
        assert cancelled.status == TaskStatus.CANCELLED

    def test_cancel_completed_task(self) -> None:
        """Test cancelling a completed task (should not change)."""
        queue = TaskQueue()
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)
        queue.update_task(task_id, status=TaskStatus.COMPLETED)

        cancelled = queue.cancel_task(task_id)
        assert cancelled is not None
        assert cancelled.status == TaskStatus.COMPLETED

    def test_clear_completed_tasks(self) -> None:
        """Test clearing completed tasks."""
        queue = TaskQueue()
        task_id1 = queue.enqueue(TaskType.IMPORT_VIDEOS)
        task_id2 = queue.enqueue(TaskType.INDEX_VIDEO)

        queue.update_task(task_id1, status=TaskStatus.COMPLETED)

        # Clear tasks older than 0 seconds (should clear immediately)
        removed = queue.clear_completed(older_than_seconds=0)
        assert removed == 1

        # Verify task is removed
        task = queue.get_task(task_id1)
        assert task is None

        # Verify other task still exists
        task = queue.get_task(task_id2)
        assert task is not None

    def test_get_stats(self) -> None:
        """Test getting queue statistics."""
        queue = TaskQueue()
        task_id1 = queue.enqueue(TaskType.IMPORT_VIDEOS)
        task_id2 = queue.enqueue(TaskType.INDEX_VIDEO)
        task_id3 = queue.enqueue(TaskType.GENERATE_SUMMARY)

        queue.dequeue()  # Move one to running
        queue.update_task(task_id2, status=TaskStatus.COMPLETED)
        queue.update_task(task_id3, status=TaskStatus.FAILED)

        stats = queue.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 0
        assert stats["running"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1

    def test_task_timestamps(self) -> None:
        """Test task timestamps are set correctly."""
        queue = TaskQueue()
        before = int(time.time())
        task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)
        after = int(time.time())

        task = queue.get_task(task_id)
        assert task is not None
        assert before <= task.created_at <= after
        assert before <= task.updated_at <= after

    def test_task_to_dict(self) -> None:
        """Test converting task to dictionary."""
        task = Task(
            task_id="test-123",
            task_type=TaskType.IMPORT_VIDEOS,
            status=TaskStatus.RUNNING,
            progress=50,
        )

        data = task.to_dict()
        assert data["task_id"] == "test-123"
        assert data["task_type"] == "import_videos"
        assert data["status"] == "running"
        assert data["progress"] == 50

    def test_task_from_dict(self) -> None:
        """Test creating task from dictionary."""
        data = {
            "task_id": "test-123",
            "task_type": "import_videos",
            "status": "running",
            "progress": 50,
            "total": 100,
            "completed": 50,
            "error": None,
            "created_at": 1234567890,
            "updated_at": 1234567890,
            "result": None,
            "metadata": {},
        }

        task = Task.from_dict(data)
        assert task.task_id == "test-123"
        assert task.task_type == TaskType.IMPORT_VIDEOS
        assert task.status == TaskStatus.RUNNING
        assert task.progress == 50

    def test_concurrent_operations(self) -> None:
        """Test concurrent queue operations."""
        import threading

        queue = TaskQueue()
        results = []

        def enqueue_tasks():
            for _ in range(10):
                task_id = queue.enqueue(TaskType.IMPORT_VIDEOS)
                results.append(task_id)

        threads = [threading.Thread(target=enqueue_tasks) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 30
        stats = queue.get_stats()
        assert stats["total"] == 30
