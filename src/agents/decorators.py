"""@action decorator — declarative way to define agent actions with metadata."""

from __future__ import annotations

from typing import Any, Callable


def action(name: str | None = None, description: str = ""):
    """Decorator to mark a method as an agent action.

    Usage:
        class MyAgent(BaseAgent):
            @action(description="Greet someone by name")
            async def greet(self, payload):
                ...

            @action(name="run_search", description="Run a web search")
            async def _internal_search(self, payload):
                ...

    The decorated method gets ``_action_meta`` with name and description.
    BaseAgent.capabilities() and BaseAgent.describe() pick these up
    automatically.
    """

    def decorator(func: Callable) -> Callable:
        func._action_meta = {
            "name": name or func.__name__,
            "description": description,
        }
        return func

    return decorator


def get_action_methods(agent: Any) -> dict[str, dict[str, Any]]:
    """Collect all @action-decorated methods from an agent instance.

    Returns: {action_name: {"handler": method, "description": str}}
    """
    actions = {}
    for attr_name in dir(agent):
        method = getattr(agent, attr_name, None)
        if callable(method) and hasattr(method, "_action_meta"):
            meta = method._action_meta
            actions[meta["name"]] = {
                "handler": method,
                "description": meta["description"],
            }
    return actions
