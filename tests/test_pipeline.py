"""End-to-end tests for the messaging pipeline."""

import pytest

from src.adapters.webhook import WebhookAdapter
from src.agents.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.schemas import NotificationStatus
from src.services.messaging import MessagingService
from src.services.orchestrator import Orchestrator


@pytest.fixture
def pipeline():
    registry = AgentRegistry()
    registry.register(ResearchAgent())
    orchestrator = Orchestrator(registry)
    svc = MessagingService(orchestrator)
    svc.register_adapter(WebhookAdapter())
    return svc


@pytest.mark.asyncio
async def test_full_pipeline_success(pipeline):
    raw = {
        "user_id": "u1",
        "namespace": "research_agent",
        "action": "run_autonomous_research",
        "parameters": {"query": "Quantum Computing"},
    }
    notif = await pipeline.handle_incoming("webhook", raw)
    assert notif.status == NotificationStatus.COMPLETED
    assert "Quantum Computing" in (notif.message or "")


@pytest.mark.asyncio
async def test_unknown_namespace(pipeline):
    raw = {
        "user_id": "u1",
        "namespace": "nonexistent_agent",
        "action": "do_thing",
    }
    notif = await pipeline.handle_incoming("webhook", raw)
    assert notif.status == NotificationStatus.FAILED
    assert "nonexistent_agent" in (notif.message or "")


@pytest.mark.asyncio
async def test_unknown_action(pipeline):
    raw = {
        "user_id": "u1",
        "namespace": "research_agent",
        "action": "nonexistent_action",
    }
    notif = await pipeline.handle_incoming("webhook", raw)
    assert notif.status == NotificationStatus.FAILED
    assert "Unknown action" in (notif.message or "")


@pytest.mark.asyncio
async def test_summarize_action(pipeline):
    raw = {
        "user_id": "u1",
        "namespace": "research_agent",
        "action": "summarize",
        "parameters": {"query": "A long body of text for summarization."},
    }
    notif = await pipeline.handle_incoming("webhook", raw)
    assert notif.status == NotificationStatus.COMPLETED
    assert "Summary" in (notif.message or "")
