"""Base agent interface — every agent must implement this contract."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from src.schemas import AgentPayload, Notification

if TYPE_CHECKING:
    from src.services.orchestrator import Orchestrator


class BaseAgent(abc.ABC):
    """Abstract base class for all agents in the system.

    Subclasses must declare ``namespace`` and implement ``handle``.

    If ``orchestrator`` is set (done automatically during registration),
    the agent can call other agents via ``self.call_agent()``.
    """

    namespace: str  # e.g. "research_agent"
    orchestrator: Orchestrator | None = None

    @abc.abstractmethod
    async def handle(self, payload: AgentPayload) -> Notification:
        """Execute the requested action and return a Notification."""

    async def call_agent(
        self,
        target_namespace: str,
        action: str,
        parameters: dict | None = None,
        parent_payload: AgentPayload | None = None,
    ) -> Notification:
        """Call another agent through the orchestrator (A2A)."""
        if self.orchestrator is None:
            raise RuntimeError(
                f"Agent '{self.namespace}' has no orchestrator reference. "
                "Cannot make A2A calls."
            )
        return await self.orchestrator.agent_call(
            caller_namespace=self.namespace,
            target_namespace=target_namespace,
            action=action,
            parameters=parameters,
            parent_payload=parent_payload,
        )

    def capabilities(self) -> list[str]:
        """Return a list of action names this agent supports.

        Default implementation introspects ``action_*`` methods.
        """
        return [
            name.removeprefix("action_")
            for name in dir(self)
            if name.startswith("action_") and callable(getattr(self, name))
        ]

    def describe(self) -> dict[str, Any]:
        """Return a machine-readable description of this agent."""
        return {
            "namespace": self.namespace,
            "capabilities": self.capabilities(),
        }
