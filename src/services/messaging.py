"""Messaging Service — the single entry point that bridges channels to the orchestrator."""

from __future__ import annotations

import logging

from src.adapters.base import BaseChannelAdapter
from src.schemas import Notification
from src.services.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class MessagingService:
    """Channel-agnostic messaging pipeline.

    Flow:
        raw payload → adapter.parse_incoming → Command
        Command → orchestrator.dispatch → Notification
        Notification → adapter.send_notification → channel delivery
    """

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator
        self._adapters: dict[str, BaseChannelAdapter] = {}

    def register_adapter(self, adapter: BaseChannelAdapter) -> None:
        self._adapters[adapter.channel_name] = adapter
        logger.info("Registered channel adapter: %s", adapter.channel_name)

    def get_adapter(self, channel: str) -> BaseChannelAdapter | None:
        return self._adapters.get(channel)

    async def handle_incoming(
        self, channel: str, raw_payload: dict
    ) -> Notification:
        """Process an incoming payload end-to-end and return the Notification."""
        adapter = self._adapters.get(channel)
        if adapter is None:
            raise ValueError(f"No adapter registered for channel '{channel}'")

        command = await adapter.parse_incoming(raw_payload)
        logger.info(
            "Received command %s from %s → %s:%s",
            command.command_id,
            channel,
            command.namespace,
            command.action,
        )

        notification = await self.orchestrator.dispatch(command)

        # Deliver the response back through the originating channel
        await adapter.send_notification(notification)

        return notification
