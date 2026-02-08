"""Base agent interface — every agent must implement this contract."""

from __future__ import annotations

import abc
from typing import Any

from src.schemas import AgentPayload, Notification


class BaseAgent(abc.ABC):
    """Abstract base class for all agents in the system.

    Subclasses must declare ``namespace`` and implement ``handle``.
    """

    namespace: str  # e.g. "research_agent"

    @abc.abstractmethod
    async def handle(self, payload: AgentPayload) -> Notification:
        """Execute the requested action and return a Notification."""

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
