"""Tests for the async task queue."""

import asyncio

import pytest

from src.schemas import Notification, NotificationStatus
from src.services.task_queue import TaskQueue


@pytest.fixture
def queue():
    return TaskQueue()


@pytest.mark.asyncio
async def test_submit_and_get_result(queue):
    async def work():
        await asyncio.sleep(0.05)
        return Notification(
            task_id="t1",
            command_id="c1",
            status=NotificationStatus.COMPLETED,
            target_channel="test",
            target_user_id="u1",
            message="Done",
        )

    queue.submit("t1", work())
    assert queue.get_status("t1") == "in_progress"

    await asyncio.sleep(0.2)
    assert queue.get_status("t1") == "completed"
    result = queue.get_result("t1")
    assert result is not None
    assert result.message == "Done"


@pytest.mark.asyncio
async def test_task_failure_captured(queue):
    async def failing_work():
        raise ValueError("boom")

    queue.submit("t2", failing_work())
    await asyncio.sleep(0.2)
    result = queue.get_result("t2")
    assert result is not None
    assert result.status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_cancel_task(queue):
    async def slow_work():
        await asyncio.sleep(10)
        return Notification(
            task_id="t3", command_id="c1",
            status=NotificationStatus.COMPLETED,
            target_channel="test", target_user_id="u1",
        )

    queue.submit("t3", slow_work())
    cancelled = await queue.cancel("t3")
    assert cancelled is True
    assert queue.get_status("t3") == "unknown"


def test_unknown_task_status(queue):
    assert queue.get_status("nonexistent") == "unknown"


@pytest.mark.asyncio
async def test_list_tasks(queue):
    async def work():
        await asyncio.sleep(0.05)
        return Notification(
            task_id="t4", command_id="c1",
            status=NotificationStatus.COMPLETED,
            target_channel="test", target_user_id="u1",
        )

    queue.submit("t4", work())
    summary = queue.list_tasks()
    assert "t4" in summary["running"]

    await asyncio.sleep(0.2)
    summary = queue.list_tasks()
    assert "t4" in summary["completed"]
