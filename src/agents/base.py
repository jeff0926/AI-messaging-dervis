"""Base agent interface — every agent must implement this contract."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from src.agents.decorators import get_action_methods
from src.schemas import AgentPayload, Notification

if TYPE_CHECKING:
    from src.services.orchestrator import Orchestrator


class BaseAgent(abc.ABC):
    """Abstract base class for all agents in the system.

    Subclasses must declare ``namespace`` and implement ``handle``.

    Actions can be defined in three ways (all coexist):
        1. ``@action`` decorator on methods (recommended)
        2. ``action_*`` method naming convention
        3. Override ``capabilities()`` directly

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

        Discovers actions from @action-decorated methods and action_* methods.
        """
        # @action decorator methods
        decorated = list(get_action_methods(self).keys())
        # action_* convention methods
        prefixed = [
            name.removeprefix("action_")
            for name in dir(self)
            if name.startswith("action_") and callable(getattr(self, name))
        ]
        # Merge, preserving order, no duplicates
        seen = set()
        result = []
        for name in decorated + prefixed:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result

    def get_action_handler(self, action_name: str):
        """Look up a handler by action name (decorator first, then action_* prefix)."""
        decorated = get_action_methods(self)
        if action_name in decorated:
            return decorated[action_name]["handler"]
        prefixed = getattr(self, f"action_{action_name}", None)
        if prefixed and callable(prefixed):
            return prefixed
        return None

    def describe(self) -> dict[str, Any]:
        """Return a machine-readable description of this agent."""
        decorated = get_action_methods(self)
        actions_with_desc = {}
        for cap in self.capabilities():
            if cap in decorated and decorated[cap]["description"]:
                actions_with_desc[cap] = decorated[cap]["description"]
            else:
                actions_with_desc[cap] = ""
        return {
            "namespace": self.namespace,
            "capabilities": list(actions_with_desc.keys()),
            "action_descriptions": actions_with_desc,
        }
