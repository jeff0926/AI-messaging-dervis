"""Tests for Agent-to-Agent communication."""

import pytest

from src.agents.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.schemas import AgentPayload, NotificationStatus
from src.services.orchestrator import Orchestrator


@pytest.fixture
def orchestrator():
    registry = AgentRegistry()
    registry.register(ResearchAgent())
    orch = Orchestrator(registry)
    registry.set_orchestrator(orch)
    return orch


@pytest.mark.asyncio
async def test_agent_call_success(orchestrator):
    result = await orchestrator.agent_call(
        caller_namespace="test_caller",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "Some text to summarize"},
    )
    assert result.status == NotificationStatus.COMPLETED
    assert "Summary" in (result.message or "")


@pytest.mark.asyncio
async def test_agent_call_unknown_target(orchestrator):
    result = await orchestrator.agent_call(
        caller_namespace="test_caller",
        target_namespace="nonexistent",
        action="do_thing",
    )
    assert result.status == NotificationStatus.FAILED
    assert "nonexistent" in (result.message or "")


@pytest.mark.asyncio
async def test_agent_call_with_parent_payload(orchestrator):
    parent = AgentPayload(
        command_id="cmd-123",
        namespace="research_agent",
        action="summarize",
        context={"user_id": "u1", "source_channel": "telegram"},
    )
    result = await orchestrator.agent_call(
        caller_namespace="test_caller",
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "Hello world"},
        parent_payload=parent,
    )
    assert result.status == NotificationStatus.COMPLETED
    assert result.command_id == "cmd-123"


@pytest.mark.asyncio
async def test_call_agent_from_agent(orchestrator):
    """Test that an agent can use self.call_agent()."""
    agent = orchestrator.registry.get("research_agent")
    assert agent is not None
    assert agent.orchestrator is not None

    result = await agent.call_agent(
        target_namespace="research_agent",
        action="summarize",
        parameters={"query": "Self-referential test"},
    )
    assert result.status == NotificationStatus.COMPLETED
