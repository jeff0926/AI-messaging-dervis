"""Tests for the Telegram adapter's command parsing."""

import pytest

from src.adapters.telegram import TelegramAdapter


@pytest.fixture
def adapter():
    return TelegramAdapter(bot_token="test-token")


@pytest.mark.asyncio
async def test_parse_slash_space_style(adapter):
    raw = {
        "message": {
            "text": '/research_agent run_autonomous_research "Quantum Computing"',
            "from": {"id": 42},
            "chat": {"id": 100},
        }
    }
    cmd = await adapter.parse_incoming(raw)
    assert cmd.namespace == "research_agent"
    assert cmd.action == "run_autonomous_research"
    assert cmd.parameters["query"] == "Quantum Computing"
    assert cmd.metadata["chat_id"] == "100"


@pytest.mark.asyncio
async def test_parse_colon_style(adapter):
    raw = {
        "message": {
            "text": "/research_agent:summarize Some text here",
            "from": {"id": 7},
            "chat": {"id": 200},
        }
    }
    cmd = await adapter.parse_incoming(raw)
    assert cmd.namespace == "research_agent"
    assert cmd.action == "summarize"
    assert cmd.parameters["query"] == "Some text here"


@pytest.mark.asyncio
async def test_parse_no_params(adapter):
    raw = {
        "message": {
            "text": "/research_agent status",
            "from": {"id": 1},
            "chat": {"id": 300},
        }
    }
    cmd = await adapter.parse_incoming(raw)
    assert cmd.namespace == "research_agent"
    assert cmd.action == "status"
    assert cmd.parameters == {}
