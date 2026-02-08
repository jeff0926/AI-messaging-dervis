"""Telegram Channel Adapter — translates between Telegram API and canonical schemas."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from src.adapters.base import BaseChannelAdapter
from src.schemas import Command, Notification

logger = logging.getLogger(__name__)

# Matches: /namespace action "param1" param2  OR  /namespace:action param1 param2
_CMD_PATTERN = re.compile(
    r"^/(?P<namespace>\w+)(?::(?P<action_colon>\w+))?"
    r"(?:\s+(?P<rest>.+))?$",
    re.DOTALL,
)


class TelegramAdapter(BaseChannelAdapter):
    """Adapter for the Telegram Bot API."""

    channel_name = "telegram"

    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token
        self._api_base = f"https://api.telegram.org/bot{bot_token}"

    # ------------------------------------------------------------------
    # Incoming: Telegram update → Command
    # ------------------------------------------------------------------
    async def parse_incoming(self, raw: dict) -> Command:
        """Parse a Telegram webhook update into a Command.

        Supports two command styles:
            /research_agent run_autonomous_research "Quantum Computing"
            /research_agent:run_autonomous_research "Quantum Computing"
        """
        message: dict[str, Any] = raw.get("message", {})
        text: str = message.get("text", "")
        user_id = str(message.get("from", {}).get("id", "unknown"))
        chat_id = str(message.get("chat", {}).get("id", ""))

        namespace, action, params = self._parse_text(text)

        return Command(
            user_id=user_id,
            source_channel=self.channel_name,
            namespace=namespace,
            action=action,
            parameters=params,
            raw_text=text,
            metadata={"chat_id": chat_id, "telegram_update": raw},
        )

    @staticmethod
    def _parse_text(text: str) -> tuple[str, str, dict[str, Any]]:
        """Extract namespace, action, and parameters from raw text."""
        match = _CMD_PATTERN.match(text.strip())
        if not match:
            return "unknown", "unknown", {"raw": text}

        namespace = match.group("namespace")
        rest = (match.group("rest") or "").strip()

        # If action was given via colon syntax: /ns:action ...
        action_from_colon = match.group("action_colon")
        if action_from_colon:
            action = action_from_colon
            query = rest
        else:
            # First token of rest is the action
            parts = rest.split(None, 1)
            action = parts[0] if parts else "default"
            query = parts[1] if len(parts) > 1 else ""

        # Strip surrounding quotes from the query
        query = query.strip().strip("\"'")

        return namespace, action, {"query": query} if query else {}

    # ------------------------------------------------------------------
    # Outgoing: Notification → Telegram sendMessage
    # ------------------------------------------------------------------
    async def send_notification(self, notification: Notification) -> None:
        """Deliver a Notification as a Telegram message."""
        chat_id = notification.data.get("chat_id") or notification.target_user_id
        text = self._format_message(notification)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._api_base}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            if resp.status_code != 200:
                logger.error("Telegram sendMessage failed: %s", resp.text)

    @staticmethod
    def _format_message(notification: Notification) -> str:
        """Build a human-readable Telegram message from a Notification."""
        parts: list[str] = []
        status_icon = {
            "pending": "\u23f3",
            "in_progress": "\u2699\ufe0f",
            "completed": "\u2705",
            "failed": "\u274c",
        }.get(notification.status.value, "")

        parts.append(f"{status_icon} *Status:* {notification.status.value}")
        if notification.message:
            parts.append(notification.message)
        return "\n\n".join(parts)
