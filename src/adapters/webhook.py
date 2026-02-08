"""Generic Webhook Adapter — for direct HTTP/JSON callers (Slack, custom UIs, etc.)."""

from __future__ import annotations

import logging

from src.adapters.base import BaseChannelAdapter
from src.schemas import Command, Notification

logger = logging.getLogger(__name__)


class WebhookAdapter(BaseChannelAdapter):
    """Pass-through adapter for already-structured JSON payloads.

    Callers POST a JSON body that maps directly to the Command schema, so
    minimal transformation is needed. This makes it trivial for Slack bots,
    web frontends, or other services to integrate.
    """

    channel_name = "webhook"

    async def parse_incoming(self, raw: dict) -> Command:
        return Command(
            user_id=raw["user_id"],
            source_channel=raw.get("source_channel", self.channel_name),
            namespace=raw["namespace"],
            action=raw["action"],
            parameters=raw.get("parameters", {}),
            raw_text=raw.get("raw_text"),
            metadata=raw.get("metadata", {}),
        )

    async def send_notification(self, notification: Notification) -> None:
        # For webhook callers the notification is returned synchronously in
        # the HTTP response, so this is a no-op.
        logger.debug("Webhook adapter: notification returned inline.")
