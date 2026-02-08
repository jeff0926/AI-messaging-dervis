"""FastAPI application — HTTP entrypoint for the messaging pipeline."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request

from src.adapters.telegram import TelegramAdapter
from src.adapters.webhook import WebhookAdapter
from src.agents.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.services.messaging import MessagingService
from src.services.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

registry = AgentRegistry()
registry.register(ResearchAgent())

orchestrator = Orchestrator(registry)
messaging = MessagingService(orchestrator)

# Register channel adapters
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
if telegram_token:
    messaging.register_adapter(TelegramAdapter(bot_token=telegram_token))

messaging.register_adapter(WebhookAdapter())

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Multi-Agent Messaging Service",
    version="0.1.0",
    description="Namespace-routed messaging pipeline for autonomous agents.",
)


@app.get("/health")
async def health():
    return {"status": "ok", "agents": registry.namespaces}


@app.get("/agents")
async def list_agents():
    """Return all registered agents and their capabilities."""
    return {"agents": registry.list_agents()}


@app.post("/webhook/{channel}")
async def incoming_webhook(channel: str, request: Request):
    """Generic webhook endpoint.

    ``channel`` should match a registered adapter name (``telegram``, ``webhook``, …).
    """
    body = await request.json()
    try:
        notification = await messaging.handle_incoming(channel, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return notification.model_dump(mode="json")


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Convenience endpoint for Telegram's webhook callback."""
    body = await request.json()
    if messaging.get_adapter("telegram") is None:
        raise HTTPException(status_code=503, detail="Telegram adapter not configured")
    notification = await messaging.handle_incoming("telegram", body)
    return notification.model_dump(mode="json")
