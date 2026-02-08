"""Telegram polling mode — pulls updates from Telegram without needing a public URL."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.telegram import TelegramAdapter
from src.adapters.webhook import WebhookAdapter
from src.agents.agent_manager import AgentManager
from src.agents.registry import AgentRegistry
from src.agents.research_agent import ResearchAgent
from src.services.messaging import MessagingService
from src.services.orchestrator import Orchestrator

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    # Bootstrap the pipeline
    registry = AgentRegistry()
    registry.register(ResearchAgent())
    registry.register(AgentManager(registry))

    orchestrator = Orchestrator(registry)
    messaging = MessagingService(orchestrator)

    telegram_adapter = TelegramAdapter(bot_token=token)
    messaging.register_adapter(telegram_adapter)
    messaging.register_adapter(WebhookAdapter())

    api_base = f"https://api.telegram.org/bot{token}"
    offset = 0

    # Verify bot token
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/getMe")
        if resp.status_code != 200:
            logger.error("Invalid bot token: %s", resp.text)
            sys.exit(1)
        bot_info = resp.json()["result"]
        logger.info(
            "Bot connected: @%s (%s)",
            bot_info.get("username"),
            bot_info.get("first_name"),
        )

    # Delete any existing webhook so polling works
    async with httpx.AsyncClient() as client:
        await client.get(f"{api_base}/deleteWebhook")

    logger.info("Polling for messages... Send a command to your bot in Telegram.")

    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            try:
                resp = await client.get(
                    f"{api_base}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                if resp.status_code != 200:
                    logger.error("getUpdates failed: %s", resp.text)
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                updates = resp.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1

                    if "message" not in update:
                        continue

                    text = update["message"].get("text", "")
                    chat_id = update["message"]["chat"]["id"]
                    user = update["message"].get("from", {})
                    logger.info(
                        "Message from %s (chat %s): %s",
                        user.get("username", user.get("id")),
                        chat_id,
                        text,
                    )

                    if not text.startswith("/"):
                        # Send a help message for non-command text
                        await client.post(
                            f"{api_base}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": (
                                    "Send a command like:\n"
                                    '/research_agent run_autonomous_research "Quantum Computing"\n\n'
                                    "Available agents: "
                                    + ", ".join(registry.namespaces)
                                ),
                            },
                        )
                        continue

                    # Process through the full pipeline
                    try:
                        notification = await messaging.handle_incoming(
                            "telegram", update
                        )
                        logger.info(
                            "Response: %s — %s",
                            notification.status.value,
                            notification.message,
                        )
                    except Exception:
                        logger.exception("Error processing message")

            except httpx.ReadTimeout:
                continue
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception:
                logger.exception("Polling error")
                await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
