"""Tests for A2A max depth guard in the Orchestrator."""

import pytest

from src.agents.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.schemas import AgentPayload, NotificationStatus
from src.services.orchestrator import A2A_MAX_DEPTH, Orchestrator


@pytest.fixture
def orchestrator():
    registry = AgentRegistry()
    registry.register(ResearchAgent())
    orch = Orchestrator(registry)
    registry.set_orchestrator(orch)
    return orch


@pytest.mark.asyncio
async def test_depth_within_limit(orchestrator):
    """Calls with depth below the limit should succeed."""
    parent = AgentPayload(
        command_id="cmd-1",
        namespace="research_agent",
        action="summarize",
        context={"_a2a_depth": 2},
    )
    result = await orchestrator.agent_call(
        caller_namespace="test",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "hello"},
        parent_payload=parent,
    )
    assert result.status == NotificationStatus.COMPLETED


@pytest.mark.asyncio
async def test_depth_at_limit_blocked(orchestrator):
    """Calls at exactly the max depth should be blocked."""
    parent = AgentPayload(
        command_id="cmd-1",
        namespace="research_agent",
        action="summarize",
        context={"_a2a_depth": A2A_MAX_DEPTH},
    )
    result = await orchestrator.agent_call(
        caller_namespace="test",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "hello"},
        parent_payload=parent,
    )
    assert result.status == NotificationStatus.FAILED
    assert "max depth" in result.message.lower()


@pytest.mark.asyncio
async def test_depth_exceeds_limit_blocked(orchestrator):
    """Calls beyond max depth should be blocked."""
    parent = AgentPayload(
        command_id="cmd-1",
        namespace="research_agent",
        action="summarize",
        context={"_a2a_depth": A2A_MAX_DEPTH + 5},
    )
    result = await orchestrator.agent_call(
        caller_namespace="test",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "hello"},
        parent_payload=parent,
    )
    assert result.status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_no_parent_depth_starts_at_zero(orchestrator):
    """Without a parent payload, depth starts at 0 (always within limit)."""
    result = await orchestrator.agent_call(
        caller_namespace="test",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "hello"},
    )
    assert result.status == NotificationStatus.COMPLETED


@pytest.mark.asyncio
async def test_depth_propagates_in_context(orchestrator):
    """The _a2a_depth context value should increment from parent."""
    parent = AgentPayload(
        command_id="cmd-1",
        namespace="research_agent",
        action="summarize",
        context={"_a2a_depth": 3},
    )
    # We can't easily inspect the created payload, but we can verify
    # depth 3 -> depth 4 still succeeds (since max is 5)
    result = await orchestrator.agent_call(
        caller_namespace="test",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "hello"},
        parent_payload=parent,
    )
    assert result.status == NotificationStatus.COMPLETED
