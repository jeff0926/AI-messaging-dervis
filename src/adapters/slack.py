"""Slack Channel Adapter — translates between Slack Events API and canonical schemas."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from typing import Any

import httpx

from src.adapters.base import BaseChannelAdapter
from src.schemas import Command, Notification

logger = logging.getLogger(__name__)

_CMD_PATTERN = re.compile(
    r"^/(?P<namespace>\w+)(?::(?P<action_colon>\w+))?"
    r"(?:\s+(?P<rest>.+))?$",
    re.DOTALL,
)


class SlackAdapter(BaseChannelAdapter):
    """Adapter for the Slack Bot API (Events + Web API)."""

    channel_name = "slack"

    def __init__(self, bot_token: str, signing_secret: str = "") -> None:
        self.bot_token = bot_token
        self.signing_secret = signing_secret

    def verify_signature(self, timestamp: str, body: str, signature: str) -> bool:
        """Verify a Slack request signature."""
        if not self.signing_secret:
            return True
        if abs(time.time() - int(timestamp)) > 300:
            return False
        sig_basestring = f"v0:{timestamp}:{body}"
        computed = "v0=" + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def parse_incoming(self, raw: dict) -> Command:
        """Parse a Slack event payload into a Command.

        Handles both slash commands and message events.
        """
        # Slash command payload
        if "command" in raw:
            return self._parse_slash_command(raw)

        # Events API payload
        event = raw.get("event", {})
        text = event.get("text", "")
        user_id = event.get("user", "unknown")
        channel_id = event.get("channel", "")

        namespace, action, params = self._parse_text(text)

        return Command(
            user_id=user_id,
            source_channel=self.channel_name,
            namespace=namespace,
            action=action,
            parameters=params,
            raw_text=text,
            metadata={
                "channel_id": channel_id,
                "thread_ts": event.get("thread_ts", event.get("ts", "")),
                "team_id": raw.get("team_id", ""),
            },
        )

    def _parse_slash_command(self, raw: dict) -> Command:
        """Parse a Slack slash command (e.g. /research_agent run query)."""
        command_name = raw.get("command", "").lstrip("/")
        text = raw.get("text", "")
        parts = text.split(None, 1)
        action = parts[0] if parts else "default"
        query = parts[1].strip("\"'") if len(parts) > 1 else ""

        return Command(
            user_id=raw.get("user_id", "unknown"),
            source_channel=self.channel_name,
            namespace=command_name,
            action=action,
            parameters={"query": query} if query else {},
            raw_text=f"/{command_name} {text}",
            metadata={
                "channel_id": raw.get("channel_id", ""),
                "response_url": raw.get("response_url", ""),
                "team_id": raw.get("team_id", ""),
            },
        )

    @staticmethod
    def _parse_text(text: str) -> tuple[str, str, dict[str, Any]]:
        """Extract namespace, action, and parameters from message text."""
        match = _CMD_PATTERN.match(text.strip())
        if not match:
            return "unknown", "unknown", {"raw": text}

        namespace = match.group("namespace")
        rest = (match.group("rest") or "").strip()

        action_from_colon = match.group("action_colon")
        if action_from_colon:
            action = action_from_colon
            query = rest
        else:
            parts = rest.split(None, 1)
            action = parts[0] if parts else "default"
            query = parts[1] if len(parts) > 1 else ""

        query = query.strip().strip("\"'")
        return namespace, action, {"query": query} if query else {}

    async def send_notification(self, notification: Notification) -> None:
        """Deliver a Notification as a Slack message."""
        channel = (
            notification.data.get("channel_id")
            or notification.metadata.get("channel_id", "")
            if hasattr(notification, "metadata")
            else ""
        )
        if not channel:
            channel = notification.target_user_id

        text = self._format_message(notification)
        thread_ts = notification.data.get("thread_ts")

        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json=payload,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error("Slack postMessage failed: %s", data.get("error"))

    @staticmethod
    def _format_message(notification: Notification) -> str:
        """Build a Slack-formatted message from a Notification."""
        status_icon = {
            "pending": ":hourglass:",
            "in_progress": ":gear:",
            "completed": ":white_check_mark:",
            "failed": ":x:",
        }.get(notification.status.value, "")

        parts = [f"{status_icon} *Status:* {notification.status.value}"]
        if notification.message:
            parts.append(notification.message)
        return "\n\n".join(parts)
