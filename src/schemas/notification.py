"""Notification / Response Schema — defines how agents send data back."""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Notification(BaseModel):
    """Response payload that an agent sends back through the messaging pipeline."""

    task_id: str = Field(..., description="Reference to the AgentPayload task_id")
    command_id: str = Field(
        ..., description="Reference to the originating Command"
    )
    status: NotificationStatus = Field(...)
    target_channel: str = Field(
        ..., description="Channel to deliver the response to"
    )
    target_user_id: str = Field(
        ..., description="User to deliver the response to"
    )
    data: dict[str, Any] = Field(
        default_factory=dict, description="Structured response data"
    )
    message: str | None = Field(
        default=None, description="Human-readable message"
    )
    media: list[MediaAttachment] | None = Field(
        default=None, description="Files / images to attach"
    )
    transformation_hints: dict[str, Any] = Field(
        default_factory=dict,
        description="Hints for the channel adapter (formatting, buttons, etc.)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class MediaAttachment(BaseModel):
    """Attachment (file, image, document) within a Notification."""

    type: str = Field(..., description="Mime type or category (image, file, …)")
    url: str | None = None
    content_bytes: bytes | None = Field(
        default=None, description="Inline content (small payloads only)"
    )
    filename: str | None = None


# Rebuild Notification so that the forward reference to MediaAttachment resolves.
Notification.model_rebuild()
