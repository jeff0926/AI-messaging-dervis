"""Dynamic Agent — a runtime-created agent with user-defined response templates."""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.schemas import AgentPayload, Notification, NotificationStatus


class DynamicAgent(BaseAgent):
    """An agent created at runtime via Telegram commands.

    Each action maps to a response template string. Templates can use
    ``{query}`` as a placeholder for the user's input.
    """

    def __init__(self, namespace: str, description: str = "") -> None:
        self.namespace = namespace
        self.description = description
        self._actions: dict[str, str] = {}

    def add_action(self, action_name: str, response_template: str) -> None:
        self._actions[action_name] = response_template

    def remove_action(self, action_name: str) -> bool:
        return self._actions.pop(action_name, None) is not None

    def capabilities(self) -> list[str]:
        return list(self._actions.keys())

    def describe(self) -> dict:
        return {
            "namespace": self.namespace,
            "description": self.description,
            "capabilities": self.capabilities(),
        }

    async def handle(self, payload: AgentPayload) -> Notification:
        template = self._actions.get(payload.action)
        if template is None:
            return Notification(
                task_id=payload.task_id,
                command_id=payload.command_id,
                status=NotificationStatus.FAILED,
                target_channel=payload.context.get("source_channel", "unknown"),
                target_user_id=payload.context.get("user_id", "unknown"),
                data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
                message=f"Unknown action: {payload.action}\n"
                f"Available: {self.capabilities()}",
            )

        query = payload.payload.get("query", "")
        message = template.replace("{query}", query)

        return Notification(
            task_id=payload.task_id,
            command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
            message=message,
        )
