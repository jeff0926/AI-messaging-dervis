"""Command Schema — defines the structure of incoming requests from any channel."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Command(BaseModel):
    """Incoming command parsed from any messaging channel.

    The namespace:action pattern (e.g. ``research_agent:run_autonomous_research``)
    is the primary routing key used by the Orchestrator.
    """

    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="Channel-agnostic user identifier")
    source_channel: str = Field(
        ..., description="Originating channel (telegram, slack, webhook, …)"
    )
    namespace: str = Field(
        ..., description="Target agent namespace (e.g. research_agent)"
    )
    action: str = Field(
        ..., description="Action to invoke on the agent (e.g. run_autonomous_research)"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Free-form parameters for the action"
    )
    raw_text: str | None = Field(
        default=None, description="Original raw text from the user"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra context (reply-to message id, thread id, etc.)",
    )
