"""Orchestrator — central brain that routes commands to agents via the registry."""

from __future__ import annotations

import logging

from src.agents.registry import AgentRegistry
from src.schemas import AgentPayload, Command, Notification, NotificationStatus

logger = logging.getLogger(__name__)


class Orchestrator:
    """Receives Commands, resolves the target agent via the Registry, and dispatches."""

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    async def dispatch(self, command: Command) -> Notification:
        """Route a Command to the appropriate agent and return its Notification."""
        agent = self.registry.get(command.namespace)
        if agent is None:
            logger.warning("No agent found for namespace: %s", command.namespace)
            return Notification(
                task_id="",
                command_id=command.command_id,
                status=NotificationStatus.FAILED,
                target_channel=command.source_channel,
                target_user_id=command.user_id,
                message=f"Unknown agent namespace: '{command.namespace}'. "
                f"Available: {self.registry.namespaces}",
            )

        payload = AgentPayload.from_command(command)
        logger.info(
            "Dispatching task %s → %s:%s",
            payload.task_id,
            command.namespace,
            command.action,
        )

        try:
            notification = await agent.handle(payload)
        except Exception:
            logger.exception("Agent %s raised an exception", command.namespace)
            notification = Notification(
                task_id=payload.task_id,
                command_id=command.command_id,
                status=NotificationStatus.FAILED,
                target_channel=command.source_channel,
                target_user_id=command.user_id,
                message="Internal agent error — see server logs.",
            )

        return notification
