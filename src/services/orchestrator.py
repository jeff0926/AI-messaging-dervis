"""Orchestrator — central brain that routes commands to agents via the registry."""

from __future__ import annotations

import logging
import uuid

from src.agents.registry import AgentRegistry
from src.schemas import AgentPayload, Command, Notification, NotificationStatus

logger = logging.getLogger(__name__)


class Orchestrator:
    """Receives Commands, resolves the target agent via the Registry, and dispatches.

    Also provides ``agent_call`` for agent-to-agent communication.
    """

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

    async def agent_call(
        self,
        caller_namespace: str,
        target_namespace: str,
        action: str,
        parameters: dict | None = None,
        parent_payload: AgentPayload | None = None,
    ) -> Notification:
        """Allow one agent to call another through the orchestrator.

        This is the Agent-to-Agent (A2A) communication channel.
        """
        agent = self.registry.get(target_namespace)
        if agent is None:
            return Notification(
                task_id="",
                command_id=parent_payload.command_id if parent_payload else "",
                status=NotificationStatus.FAILED,
                target_channel="internal",
                target_user_id="system",
                message=f"A2A call failed: no agent '{target_namespace}'",
            )

        payload = AgentPayload(
            task_id=str(uuid.uuid4()),
            command_id=parent_payload.command_id if parent_payload else "",
            namespace=target_namespace,
            action=action,
            payload=parameters or {},
            context={
                "source_channel": "internal",
                "user_id": "system",
                "caller": caller_namespace,
                **(parent_payload.context if parent_payload else {}),
            },
        )

        logger.info(
            "A2A call: %s → %s:%s (task %s)",
            caller_namespace,
            target_namespace,
            action,
            payload.task_id,
        )

        try:
            return await agent.handle(payload)
        except Exception:
            logger.exception("A2A call to %s failed", target_namespace)
            return Notification(
                task_id=payload.task_id,
                command_id=payload.command_id,
                status=NotificationStatus.FAILED,
                target_channel="internal",
                target_user_id="system",
                message=f"A2A error calling {target_namespace}:{action}",
            )
