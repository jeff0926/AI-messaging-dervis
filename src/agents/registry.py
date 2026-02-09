"""Agent Registry — central directory of available agents and their capabilities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.services.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Thread-safe registry mapping namespaces to agent instances."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._orchestrator: Orchestrator | None = None

    def set_orchestrator(self, orchestrator: Orchestrator) -> None:
        """Set the orchestrator so agents can make A2A calls."""
        self._orchestrator = orchestrator
        for agent in self._agents.values():
            agent.orchestrator = orchestrator

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance under its namespace."""
        ns = agent.namespace
        if ns in self._agents:
            raise ValueError(f"Namespace '{ns}' is already registered")
        if self._orchestrator:
            agent.orchestrator = self._orchestrator
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
