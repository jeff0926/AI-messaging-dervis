"""Agent Registry — central directory of available agents and their capabilities."""

from __future__ import annotations

import logging
from typing import Any

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Thread-safe registry mapping namespaces to agent instances."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance under its namespace."""
        ns = agent.namespace
        if ns in self._agents:
            raise ValueError(f"Namespace '{ns}' is already registered")
        self._agents[ns] = agent
        logger.info("Registered agent: %s (actions: %s)", ns, agent.capabilities())

    def unregister(self, namespace: str) -> None:
        """Remove an agent from the registry."""
        self._agents.pop(namespace, None)

    def get(self, namespace: str) -> BaseAgent | None:
        """Look up an agent by namespace."""
        return self._agents.get(namespace)

    def list_agents(self) -> list[dict[str, Any]]:
        """Return descriptions of all registered agents."""
        return [agent.describe() for agent in self._agents.values()]

    @property
    def namespaces(self) -> list[str]:
        return list(self._agents.keys())
