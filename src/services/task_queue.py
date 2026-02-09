"""Async task queue — runs long-running agent tasks in the background."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable

from src.schemas import Notification, NotificationStatus

logger = logging.getLogger(__name__)


class TaskQueue:
    """In-process async task queue for background agent work.

    When an agent knows a task will take a long time, it can submit it
    to the queue and immediately return a "pending" Notification. The
    queue runs the work in the background and calls the callback with
    the result.

    For production, replace with Redis/Celery/RabbitMQ — the interface
    stays the same.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._results: dict[str, Notification] = {}

    def submit(
        self,
        task_id: str,
        coro: Awaitable[Notification],
        on_complete: Callable[[Notification], Awaitable[None]] | None = None,
    ) -> None:
        """Submit a coroutine to run in the background."""

        async def _wrapper():
            try:
                result = await coro
                self._results[task_id] = result
                logger.info("Task %s completed: %s", task_id, result.status.value)
                if on_complete:
                    await on_complete(result)
            except Exception:
                logger.exception("Task %s failed", task_id)
                self._results[task_id] = Notification(
                    task_id=task_id,
                    command_id="",
                    status=NotificationStatus.FAILED,
                    target_channel="internal",
                    target_user_id="system",
                    message="Background task failed — see server logs.",
                )
            finally:
                self._tasks.pop(task_id, None)

        task = asyncio.create_task(_wrapper())
        self._tasks[task_id] = task
        logger.info("Task %s submitted to queue", task_id)

    def get_result(self, task_id: str) -> Notification | None:
        """Get the result of a completed task, or None if still running."""
        return self._results.get(task_id)

    def get_status(self, task_id: str) -> str:
        """Get the status of a task."""
        if task_id in self._results:
            return self._results[task_id].status.value
        if task_id in self._tasks:
            return "in_progress"
        return "unknown"

    def list_tasks(self) -> dict[str, Any]:
        """Return a summary of all tasks."""
        return {
            "running": list(self._tasks.keys()),
            "completed": list(self._results.keys()),
        }

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._tasks.get(task_id)
        if task:
            task.cancel()
            self._tasks.pop(task_id, None)
            logger.info("Task %s cancelled", task_id)
            return True
        return False


# Singleton instance
task_queue = TaskQueue()
