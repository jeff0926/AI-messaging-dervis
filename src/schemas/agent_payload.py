"""Agent Payload Schema — defines how the Orchestrator talks to agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AgentPayload(BaseModel):
    """Payload sent from the Orchestrator to a target agent."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command_id: str = Field(
        ..., description="Back-reference to the originating Command"
    )
    namespace: str = Field(..., description="Target agent namespace")
    action: str = Field(..., description="Action for the agent to execute")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the action"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution context (user info, source channel, reply target, …)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def from_command(cls, command: "Command") -> "AgentPayload":
        from .command import Command as _Cmd  # noqa: F811

        return cls(
            command_id=command.command_id,
            namespace=command.namespace,
            action=command.action,
            payload=command.parameters,
            context={
                "user_id": command.user_id,
                "source_channel": command.source_channel,
                "metadata": command.metadata,
            },
        )
