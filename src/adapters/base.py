"""Base Channel Adapter — abstract interface for messaging channels."""

from __future__ import annotations

import abc

from src.schemas import Command, Notification


class BaseChannelAdapter(abc.ABC):
    """Every messaging channel (Telegram, Slack, Webhook, …) implements this."""

    channel_name: str  # e.g. "telegram"

    @abc.abstractmethod
    async def parse_incoming(self, raw: dict) -> Command:
        """Transform a channel-specific payload into a canonical Command."""

    @abc.abstractmethod
    async def send_notification(self, notification: Notification) -> None:
        """Transform a Notification into the channel's native format and deliver it."""
