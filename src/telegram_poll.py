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
from src.agents.claude_agent import ClaudeAgent
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


async def _send_help(client, api_base, chat_id, registry):
    """Short help nudge for non-command messages."""
    await client.post(
        f"{api_base}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": (
                "Type /help to see all agents and commands.\n\n"
                "Quick examples:\n"
                '/claude_agent ask "What is AI?"\n'
                '/research_agent summarize "Some text"\n'
                "/agent_manager list"
            ),
        },
    )



# Action examples and use cases for built-in agents
ACTION_GUIDE = {
    "claude_agent": {
        "description": "AI-powered assistant using Claude",
        "actions": {
            "ask": {
                "example": '/claude_agent ask "What causes inflation?"',
                "use_case": "General Q&A — get clear answers on any topic",
            },
            "code": {
                "example": '/claude_agent code "Write a Python function to merge two sorted lists"',
                "use_case": "Code generation — get working code with explanations",
            },
            "summarize": {
                "example": '/claude_agent summarize "Paste a long article or paragraph here"',
                "use_case": "Condense long text into key bullet points",
            },
            "analyze": {
                "example": '/claude_agent analyze "Impact of remote work on productivity"',
                "use_case": "Deep analysis — multiple perspectives with evidence",
            },
            "clear": {
                "example": "/claude_agent clear",
                "use_case": "Reset conversation history and start fresh",
            },
        },
    },
    "research_agent": {
        "description": "Autonomous research assistant",
        "actions": {
            "run_autonomous_research": {
                "example": '/research_agent run_autonomous_research "Quantum Computing"',
                "use_case": "Kick off a full research task on any topic",
            },
            "summarize": {
                "example": '/research_agent summarize "Your text here"',
                "use_case": "Quick summary of provided text",
            },
        },
    },
    "agent_manager": {
        "description": "Create and manage custom agents from chat",
        "actions": {
            "create": {
                "example": '/agent_manager create my_bot "A helpful bot"',
                "use_case": "Spin up a new custom agent on the fly",
            },
            "add_action": {
                "example": '/agent_manager add_action my_bot:greet "Hello {query}!"',
                "use_case": "Teach your agent a new command with a response template",
            },
            "list": {
                "example": "/agent_manager list",
                "use_case": "See all agents and their available commands",
            },
            "info": {
                "example": "/agent_manager info my_bot",
                "use_case": "See details about a specific agent",
            },
            "remove_action": {
                "example": "/agent_manager remove_action my_bot:greet",
                "use_case": "Remove a command from a custom agent",
            },
            "delete": {
                "example": "/agent_manager delete my_bot",
                "use_case": "Delete a custom agent entirely",
            },
            "help": {
                "example": "/agent_manager help",
                "use_case": "Show agent manager usage guide",
            },
        },
    },
}


async def _send_full_help(client, api_base, chat_id, registry):
    """Full agent directory with examples and use cases."""
    lines = ["All available agents and commands:\n"]

    for agent_desc in registry.list_agents():
        ns = agent_desc["namespace"]
        guide = ACTION_GUIDE.get(ns)

        # Agent header
        desc = (guide["description"] if guide else
                agent_desc.get("description", ""))
        lines.append(f"--- {ns} ---")
        if desc:
            lines.append(f"{desc}\n")

        caps = agent_desc.get("capabilities", [])
        if not caps:
            lines.append("  (no actions yet)\n")
            continue

        for cap in caps:
            action_guide = guide["actions"].get(cap) if guide else None
            if action_guide:
                lines.append(f"/{ns} {cap}")
                lines.append(f"  Use case: {action_guide['use_case']}")
                lines.append(f"  Example:  {action_guide['example']}")
                lines.append("")
            else:
                lines.append(f"/{ns} {cap}\n")

    lines.append("Tip: /agent_manager help — manage custom agents")

    text = "\n".join(lines)
    # Telegram has a 4096 char limit per message
    if len(text) > 4000:
        mid = len(lines) // 2
        await client.post(
            f"{api_base}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines[:mid])},
        )
        await client.post(
            f"{api_base}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines[mid:])},
        )
    else:
        await client.post(
            f"{api_base}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    # Bootstrap the pipeline
    registry = AgentRegistry()
    registry.register(ResearchAgent())
    registry.register(ClaudeAgent())
    registry.register(AgentManager(registry))

    orchestrator = Orchestrator(registry)
    registry.set_orchestrator(orchestrator)
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
                        await _send_help(client, api_base, chat_id, registry)
                        continue

                    # /help or /start → show full agent directory
                    if text.strip() in ("/help", "/start"):
                        await _send_full_help(client, api_base, chat_id, registry)
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
