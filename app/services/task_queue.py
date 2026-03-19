"""Task queue system for background job processing."""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type enumeration."""
    IMPORT_VIDEOS = "import_videos"
    INDEX_VIDEO = "index_video"
    GENERATE_SUMMARY = "generate_summary"
    SEARCH = "search"


@dataclass
class Task:
    """Task model for background processing."""
    task_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    total: int = 0
    completed: int = 0
    error: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))
    result: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary."""
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create task from dictionary."""
        data_copy = data.copy()
        data_copy['task_type'] = TaskType(data_copy['task_type'])
        data_copy['status'] = TaskStatus(data_copy['status'])
        return cls(**data_copy)


class TaskQueue:
    """In-memory task queue for background processing."""

    def __init__(self) -> None:
        """Initialize task queue."""
        self._tasks: dict[str, Task] = {}
        self._queue: list[str] = []
        self._lock = threading.RLock()

    def enqueue(self, task_type: TaskType, metadata: Optional[dict[str, Any]] = None) -> str:
        """Enqueue a new task.

        Args:
            task_type: Type of task to enqueue
            metadata: Optional metadata for the task

        Returns:
            Task ID
        """
        with self._lock:
            task_id = str(uuid.uuid4())
            task = Task(
                task_id=task_id,
                task_type=task_type,
                metadata=metadata or {}
            )
            self._tasks[task_id] = task
            self._queue.append(task_id)
            return task_id

    def dequeue(self) -> Optional[Task]:
        """Dequeue the next task.

        Returns:
            Next task or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            task_id = self._queue.pop(0)
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING
            task.updated_at = int(time.time())
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        completed: Optional[int] = None,
        error: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
    ) -> Optional[Task]:
        """Update task status and progress.

        Args:
            task_id: Task ID
            status: New status
            progress: Progress percentage (0-100)
            completed: Number of completed items
            error: Error message if failed
            result: Result data

        Returns:
            Updated task or None if not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = min(100, max(0, progress))
            if completed is not None:
                task.completed = completed
            if error is not None:
                task.error = error
            if result is not None:
                task.result = result

            task.updated_at = int(time.time())
            return task

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status
            skip: Number of tasks to skip
            limit: Maximum number of tasks to return

        Returns:
            Tuple of (tasks, total_count)
        """
        with self._lock:
            tasks = list(self._tasks.values())

            # Filter by status if provided
            if status is not None:
                tasks = [t for t in tasks if t.status == status]

            # Sort by created_at descending
            tasks.sort(key=lambda t: t.created_at, reverse=True)

            total = len(tasks)
            return tasks[skip : skip + limit], total

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            Updated task or None if not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.updated_at = int(time.time())

            return task

    def clear_completed(self, older_than_seconds: int = 3600) -> int:
        """Clear completed tasks older than specified time.

        Args:
            older_than_seconds: Remove tasks older than this many seconds

        Returns:
            Number of tasks removed
        """
        with self._lock:
            now = int(time.time())
            cutoff_time = now - older_than_seconds

            task_ids_to_remove = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                and task.updated_at < cutoff_time
            ]

            for task_id in task_ids_to_remove:
                del self._tasks[task_id]

            return len(task_ids_to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with queue stats
        """
        with self._lock:
            tasks = list(self._tasks.values())
            return {
                "total": len(tasks),
                "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
                "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
                "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
                "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
                "queue_length": len(self._queue),
            }
