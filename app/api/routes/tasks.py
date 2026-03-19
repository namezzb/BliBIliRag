"""Task management API routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_task_queue
from app.services.task_queue import Task, TaskQueue, TaskStatus, TaskType

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    """Task response model."""
    task_id: str
    task_type: str
    status: str
    progress: int
    total: int
    completed: int
    error: Optional[str] = None
    created_at: int
    updated_at: int
    result: Optional[dict] = None


class TaskListResponse(BaseModel):
    """Task list response model."""
    tasks: list[TaskResponse]
    total: int
    skip: int
    limit: int


class CreateTaskRequest(BaseModel):
    """Create task request model."""
    task_type: str = Field(..., pattern="^(import_videos|index_video|generate_summary|search)$")
    metadata: Optional[dict] = Field(default_factory=dict)


class UpdateTaskRequest(BaseModel):
    """Update task request model."""
    status: Optional[str] = Field(None, pattern="^(pending|running|completed|failed|cancelled)$")
    progress: Optional[int] = Field(None, ge=0, le=100)
    completed: Optional[int] = Field(None, ge=0)
    error: Optional[str] = None
    result: Optional[dict] = None


def _task_to_response(task: Task) -> TaskResponse:
    """Convert task to response model."""
    return TaskResponse(
        task_id=task.task_id,
        task_type=task.task_type.value,
        status=task.status.value,
        progress=task.progress,
        total=task.total,
        completed=task.completed,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        result=task.result,
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Create a new task.

    Args:
        request: Create task request
        task_queue: Task queue

    Returns:
        Created task
    """
    try:
        task_type = TaskType(request.task_type)
        task_id = task_queue.enqueue(task_type, request.metadata)
        task = task_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=500, detail="Failed to create task")
        return _task_to_response(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {str(e)}")


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, pattern="^(pending|running|completed|failed|cancelled)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskListResponse:
    """List tasks with optional filtering.

    Args:
        status: Filter by status
        skip: Number of tasks to skip
        limit: Maximum number of tasks to return
        task_queue: Task queue

    Returns:
        Task list response
    """
    try:
        task_status = TaskStatus(status) if status else None
        tasks, total = task_queue.list_tasks(task_status, skip, limit)
        return TaskListResponse(
            tasks=[_task_to_response(t) for t in tasks],
            total=total,
            skip=skip,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Get task by ID.

    Args:
        task_id: Task ID
        task_queue: Task queue

    Returns:
        Task response
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Update task status and progress.

    Args:
        task_id: Task ID
        request: Update request
        task_queue: Task queue

    Returns:
        Updated task response
    """
    try:
        status = TaskStatus(request.status) if request.status else None
        task = task_queue.update_task(
            task_id,
            status=status,
            progress=request.progress,
            completed=request.completed,
            error=request.error,
            result=request.result,
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return _task_to_response(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    task_queue: TaskQueue = Depends(get_task_queue),
) -> dict:
    """Cancel a task.

    Args:
        task_id: Task ID
        task_queue: Task queue

    Returns:
        Cancellation status
    """
    task = task_queue.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "status": "cancelled",
        "task_id": task_id,
    }


@router.get("/stats/overview")
async def get_stats(
    task_queue: TaskQueue = Depends(get_task_queue),
) -> dict:
    """Get task queue statistics.

    Args:
        task_queue: Task queue

    Returns:
        Queue statistics
    """
    return task_queue.get_stats()
