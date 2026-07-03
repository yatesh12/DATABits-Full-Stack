from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

from core.celery_app import celery_app

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, BackgroundTask] = {}

    def create(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> BackgroundTask:
        task = BackgroundTask(
            name=name,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        return self._tasks.get(task_id)

    def update(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        result: Any = None,
        error: Optional[str] = None,
    ) -> Optional[BackgroundTask]:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if status is not None:
            task.status = status
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = datetime.now(timezone.utc)
        return task

    def remove(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
    ) -> list[BackgroundTask]:
        if status:
            return [t for t in self._tasks.values() if t.status == status]
        return list(self._tasks.values())

    def clear_completed(self) -> int:
        completed_statuses = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        to_remove = [tid for tid, t in self._tasks.items() if t.status in completed_statuses]
        for tid in to_remove:
            self._tasks.pop(tid, None)
        return len(to_remove)


task_manager = BackgroundTaskManager()


@asynccontextmanager
async def run_in_background(
    name: str,
    metadata: Optional[dict[str, Any]] = None,
) -> AsyncGenerator[BackgroundTask, None]:
    task = task_manager.create(name, metadata)
    try:
        task.status = TaskStatus.RUNNING
        yield task
        task.status = TaskStatus.COMPLETED
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        logger.error("Background task '%s' failed: %s", name, e)
        raise
    finally:
        task.completed_at = datetime.now(timezone.utc)


async def run_async_task(
    coro: Awaitable[Any],
    name: str,
    metadata: Optional[dict[str, Any]] = None,
) -> BackgroundTask:
    async with run_in_background(name, metadata) as task:
        task.result = await coro
        return task


def celery_task_wrapper(
    task_name: str,
    args: Optional[list[Any]] = None,
    kwargs: Optional[dict[str, Any]] = None,
    countdown: int = 0,
    task_id: Optional[str] = None,
) -> str:
    task = celery_app.send_task(
        task_name,
        args=args or [],
        kwargs=kwargs or {},
        countdown=countdown,
        task_id=task_id or uuid.uuid4().hex,
    )
    return task.id


async def wait_for_celery_task(
    task_id: str,
    timeout: int = 300,
    poll_interval: float = 0.5,
) -> Any:
    from celery.result import AsyncResult

    start = asyncio.get_event_loop().time()
    while True:
        result = AsyncResult(task_id, app=celery_app)
        if result.ready():
            if result.successful():
                return result.result
            raise RuntimeError(f"Celery task failed: {result.result}")
        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError(f"Celery task {task_id} timed out")
        await asyncio.sleep(poll_interval)
