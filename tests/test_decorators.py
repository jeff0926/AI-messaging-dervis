"""Tests for @action decorator and action discovery."""

import pytest

from src.agents.base import BaseAgent
from src.agents.decorators import action, get_action_methods
from src.schemas import AgentPayload, Notification, NotificationStatus


class DecoratedAgent(BaseAgent):
    namespace = "decorated_test"

    @action(description="Say hello")
    async def greet(self, payload: AgentPayload) -> Notification:
        return Notification(
            task_id=payload.task_id, command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel="test", target_user_id="test",
            message="Hello!",
        )

    @action(name="search", description="Run a search")
    async def _internal_search(self, payload: AgentPayload) -> Notification:
        return Notification(
            task_id=payload.task_id, command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel="test", target_user_id="test",
            message="Search results",
        )

    async def action_legacy(self, payload: AgentPayload) -> Notification:
        """Legacy action using action_* convention."""
        return Notification(
            task_id=payload.task_id, command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel="test", target_user_id="test",
            message="Legacy action",
        )

    async def handle(self, payload: AgentPayload) -> Notification:
        handler = self.get_action_handler(payload.action)
        if handler:
            return await handler(payload)
        return Notification(
            task_id=payload.task_id, command_id=payload.command_id,
            status=NotificationStatus.FAILED,
            target_channel="test", target_user_id="test",
            message=f"Unknown action: {payload.action}",
        )


@pytest.fixture
def agent():
    return DecoratedAgent()


def test_get_action_methods_finds_decorated(agent):
    methods = get_action_methods(agent)
    assert "greet" in methods
    assert methods["greet"]["description"] == "Say hello"


def test_custom_action_name(agent):
    methods = get_action_methods(agent)
    assert "search" in methods
    assert methods["search"]["description"] == "Run a search"
    # _internal_search should NOT appear under its raw name
    assert "_internal_search" not in methods


def test_capabilities_includes_both_styles(agent):
    caps = agent.capabilities()
    assert "greet" in caps      # @action
    assert "search" in caps     # @action(name="search")
    assert "legacy" in caps     # action_* prefix


def test_describe_includes_descriptions(agent):
    desc = agent.describe()
    assert desc["namespace"] == "decorated_test"
    assert "greet" in desc["action_descriptions"]
    assert desc["action_descriptions"]["greet"] == "Say hello"
    assert desc["action_descriptions"]["search"] == "Run a search"


def test_get_action_handler_decorator_first(agent):
    handler = agent.get_action_handler("greet")
    assert handler is not None
    assert hasattr(handler, "_action_meta")


def test_get_action_handler_legacy_prefix(agent):
    handler = agent.get_action_handler("legacy")
    assert handler is not None


def test_get_action_handler_unknown_returns_none(agent):
    handler = agent.get_action_handler("nonexistent")
    assert handler is None


@pytest.mark.asyncio
async def test_decorated_action_executes(agent):
    payload = AgentPayload(
        command_id="cmd-1", namespace="decorated_test", action="greet",
        context={"user_id": "u1", "source_channel": "test"},
    )
    result = await agent.handle(payload)
    assert result.status == NotificationStatus.COMPLETED
    assert result.message == "Hello!"


@pytest.mark.asyncio
async def test_renamed_action_executes(agent):
    payload = AgentPayload(
        command_id="cmd-1", namespace="decorated_test", action="search",
        context={"user_id": "u1", "source_channel": "test"},
    )
    result = await agent.handle(payload)
    assert result.status == NotificationStatus.COMPLETED
    assert result.message == "Search results"
