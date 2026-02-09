"""Tests for AgentManager admin security gate."""

import pytest
from unittest.mock import patch

from src.agents.agent_manager import AgentManager, ADMIN_USER_IDS
from src.agents.registry import AgentRegistry
from src.schemas import AgentPayload, NotificationStatus


def _payload(action: str, query: str = "", user_id: str = "user123") -> AgentPayload:
    return AgentPayload(
        command_id="cmd-1",
        namespace="agent_manager",
        action=action,
        payload={"query": query},
        context={"user_id": user_id, "source_channel": "telegram"},
    )


@pytest.fixture
def registry(tmp_path):
    with patch("src.agents.agent_manager.AGENTS_DIR", tmp_path):
        reg = AgentRegistry()
        reg.register(AgentManager(reg))
        return reg


@pytest.mark.asyncio
async def test_public_actions_always_allowed(registry, tmp_path):
    """list, info, help are always public — regardless of ADMIN_USER_IDS."""
    mgr = registry.get("agent_manager")

    with patch("src.agents.agent_manager.ADMIN_USER_IDS", {"admin1"}):
        with patch("src.agents.agent_manager.AGENTS_DIR", tmp_path):
            # list — should succeed even from non-admin
            result = await mgr.handle(_payload("list", user_id="random_user"))
            assert result.status == NotificationStatus.COMPLETED

            # help — public
            result = await mgr.handle(_payload("help", user_id="random_user"))
            assert result.status == NotificationStatus.COMPLETED


@pytest.mark.asyncio
async def test_write_actions_blocked_for_non_admin(registry, tmp_path):
    """create/delete/add_action/remove_action are blocked for non-admins."""
    mgr = registry.get("agent_manager")

    with patch("src.agents.agent_manager.ADMIN_USER_IDS", {"admin1"}):
        with patch("src.agents.agent_manager.AGENTS_DIR", tmp_path):
            result = await mgr.handle(
                _payload("create", 'test_bot "A bot"', user_id="not_admin")
            )
            assert result.status == NotificationStatus.FAILED
            assert "Permission denied" in result.message


@pytest.mark.asyncio
async def test_write_actions_allowed_for_admin(registry, tmp_path):
    """Admins can create agents."""
    mgr = registry.get("agent_manager")

    with patch("src.agents.agent_manager.ADMIN_USER_IDS", {"admin1"}):
        with patch("src.agents.agent_manager.AGENTS_DIR", tmp_path):
            result = await mgr.handle(
                _payload("create", 'test_bot "A bot"', user_id="admin1")
            )
            assert result.status == NotificationStatus.COMPLETED
            assert "test_bot" in result.message


@pytest.mark.asyncio
async def test_open_mode_allows_all(registry, tmp_path):
    """When ADMIN_USER_IDS is empty, all users can do anything."""
    mgr = registry.get("agent_manager")

    with patch("src.agents.agent_manager.ADMIN_USER_IDS", set()):
        with patch("src.agents.agent_manager.AGENTS_DIR", tmp_path):
            result = await mgr.handle(
                _payload("create", 'open_bot "Anyone can create"', user_id="anyone")
            )
            assert result.status == NotificationStatus.COMPLETED
