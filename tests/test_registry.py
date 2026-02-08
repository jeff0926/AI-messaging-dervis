"""Tests for the Agent Registry."""

import pytest

from src.agents.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent


def test_register_and_lookup():
    reg = AgentRegistry()
    agent = ResearchAgent()
    reg.register(agent)
    assert reg.get("research_agent") is agent


def test_duplicate_namespace_raises():
    reg = AgentRegistry()
    reg.register(ResearchAgent())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(ResearchAgent())


def test_list_agents():
    reg = AgentRegistry()
    reg.register(ResearchAgent())
    agents = reg.list_agents()
    assert len(agents) == 1
    assert agents[0]["namespace"] == "research_agent"
    assert "run_autonomous_research" in agents[0]["capabilities"]
    assert "summarize" in agents[0]["capabilities"]


def test_unregister():
    reg = AgentRegistry()
    reg.register(ResearchAgent())
    reg.unregister("research_agent")
    assert reg.get("research_agent") is None
