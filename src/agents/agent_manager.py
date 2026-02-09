"""Agent Manager — create, configure, and remove agents from Telegram."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from src.agents.base import BaseAgent
from src.agents.dynamic_agent import DynamicAgent
from src.agents.registry import AgentRegistry
from src.schemas import AgentPayload, Notification, NotificationStatus

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(os.getenv("AGENTS_DIR", "data/agents"))

# Comma-separated Telegram user IDs that can manage agents.
# If empty, all users are allowed (open mode).
_ADMIN_IDS_RAW = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS: set[str] = {
    uid.strip() for uid in _ADMIN_IDS_RAW.split(",") if uid.strip()
}

# Actions that don't require admin (read-only)
_PUBLIC_ACTIONS = {"list", "info", "help"}


class AgentManager(BaseAgent):
    """Meta-agent that manages other agents at runtime via Telegram.

    Namespace: ``agent_manager``

    Write operations (create, delete, add_action, remove_action) are
    restricted to admin users when ADMIN_USER_IDS is set in .env.
    Read operations (list, info, help) are always public.
    """

    namespace = "agent_manager"

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_saved_agents()
        if ADMIN_USER_IDS:
            logger.info("Agent manager admin IDs: %s", ADMIN_USER_IDS)
        else:
            logger.warning("ADMIN_USER_IDS not set — agent manager is open to all users")

    async def handle(self, payload: AgentPayload) -> Notification:
        action = payload.action
        query = payload.payload.get("query", "")

        handler = {
            "create": self._create,
            "delete": self._delete,
            "add_action": self._add_action,
            "remove_action": self._remove_action,
            "list": self._list,
            "info": self._info,
            "help": self._help,
        }.get(action)

        if handler is None:
            return self._reply(payload, NotificationStatus.FAILED,
                               f"Unknown command: {action}\n\n{self._help_text()}")

        # Admin check for write operations
        if action not in _PUBLIC_ACTIONS and not self._is_admin(payload):
            return self._reply(
                payload, NotificationStatus.FAILED,
                "Permission denied. Only admins can create/modify/delete agents.\n"
                "Contact the bot owner to be added to ADMIN_USER_IDS.",
            )

        return handler(payload, query)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _create(self, payload: AgentPayload, query: str) -> Notification:
        parts = query.split(None, 1)
        name = parts[0] if parts else ""
        desc = parts[1].strip("\"'") if len(parts) > 1 else ""

        if not name:
            return self._reply(payload, NotificationStatus.FAILED,
                               'Usage: /agent_manager create my_bot "Description"')

        if self.registry.get(name):
            return self._reply(payload, NotificationStatus.FAILED,
                               f"Agent '{name}' already exists.")

        agent = DynamicAgent(namespace=name, description=desc)
        self.registry.register(agent)
        self._save_agent(agent)
        return self._reply(payload, NotificationStatus.COMPLETED,
                           f"Agent '{name}' created.\n\n"
                           f"Now add actions:\n"
                           f"/agent_manager add_action {name}:greet \"Hello {{query}}!\"")

    def _delete(self, payload: AgentPayload, query: str) -> Notification:
        name = query.strip()
        if not name:
            return self._reply(payload, NotificationStatus.FAILED,
                               "Usage: /agent_manager delete my_bot")

        if name in ("agent_manager", "research_agent"):
            return self._reply(payload, NotificationStatus.FAILED,
                               f"Cannot delete built-in agent '{name}'.")

        agent = self.registry.get(name)
        if not agent or not isinstance(agent, DynamicAgent):
            return self._reply(payload, NotificationStatus.FAILED,
                               f"No dynamic agent named '{name}'.")

        self.registry.unregister(name)
        self._delete_save(name)
        return self._reply(payload, NotificationStatus.COMPLETED,
                           f"Agent '{name}' deleted.")

    def _add_action(self, payload: AgentPayload, query: str) -> Notification:
        # Expected: "my_bot:greet Hello {query}!"
        # The Telegram adapter parses /agent_manager:add_action as namespace:action
        # but the query comes in as "my_bot:action_name response template"
        parts = query.split(None, 1)
        target = parts[0] if parts else ""
        template = parts[1].strip("\"'") if len(parts) > 1 else ""

        if ":" not in target or not template:
            return self._reply(payload, NotificationStatus.FAILED,
                               "Usage: /agent_manager add_action "
                               "my_bot:greet \"Hello {query}!\"")

        agent_name, action_name = target.split(":", 1)
        agent = self.registry.get(agent_name)
        if not agent or not isinstance(agent, DynamicAgent):
            return self._reply(payload, NotificationStatus.FAILED,
                               f"No dynamic agent named '{agent_name}'.")

        agent.add_action(action_name, template)
        self._save_agent(agent)
        return self._reply(payload, NotificationStatus.COMPLETED,
                           f"Action '{action_name}' added to '{agent_name}'.\n\n"
                           f"Try it: /{agent_name} {action_name} \"test\"")

    def _remove_action(self, payload: AgentPayload, query: str) -> Notification:
        if ":" not in query:
            return self._reply(payload, NotificationStatus.FAILED,
                               "Usage: /agent_manager remove_action my_bot:greet")

        agent_name, action_name = query.strip().split(":", 1)
        agent = self.registry.get(agent_name)
        if not agent or not isinstance(agent, DynamicAgent):
            return self._reply(payload, NotificationStatus.FAILED,
                               f"No dynamic agent named '{agent_name}'.")

        if agent.remove_action(action_name):
            self._save_agent(agent)
            return self._reply(payload, NotificationStatus.COMPLETED,
                               f"Action '{action_name}' removed from '{agent_name}'.")
        return self._reply(payload, NotificationStatus.FAILED,
                           f"Action '{action_name}' not found on '{agent_name}'.")

    def _list(self, payload: AgentPayload, query: str) -> Notification:
        agents = self.registry.list_agents()
        lines = []
        for a in agents:
            lines.append(f"/{a['namespace']}")
            if a.get("description"):
                lines.append(f"  {a['description']}")
            caps = a.get("capabilities", [])
            if caps:
                for cap in caps:
                    lines.append(f"  - /{a['namespace']} {cap}")
            else:
                lines.append("  (no actions)")
            lines.append("")  # blank line between agents
        return self._reply(
            payload, NotificationStatus.COMPLETED,
            "All registered agents:\n\n" + "\n".join(lines).rstrip(),
        )

    def _info(self, payload: AgentPayload, query: str) -> Notification:
        name = query.strip()
        agent = self.registry.get(name)
        if not agent:
            return self._reply(payload, NotificationStatus.FAILED,
                               f"No agent named '{name}'.")
        desc = agent.describe()
        caps = "\n".join(f"  - {c}" for c in desc["capabilities"]) or "  (none)"
        text = f"Agent: {desc['namespace']}\n"
        if desc.get("description"):
            text += f"Description: {desc['description']}\n"
        text += f"Actions:\n{caps}"
        return self._reply(payload, NotificationStatus.COMPLETED, text)

    def _help(self, payload: AgentPayload, query: str) -> Notification:
        return self._reply(payload, NotificationStatus.COMPLETED, self._help_text())

    # ------------------------------------------------------------------
    # Persistence — save/load agents as JSON
    # ------------------------------------------------------------------
    def _save_agent(self, agent: DynamicAgent) -> None:
        path = AGENTS_DIR / f"{agent.namespace}.json"
        path.write_text(json.dumps({
            "namespace": agent.namespace,
            "description": agent.description,
            "actions": agent._actions,
        }, indent=2))

    def _delete_save(self, name: str) -> None:
        path = AGENTS_DIR / f"{name}.json"
        path.unlink(missing_ok=True)

    def _load_saved_agents(self) -> None:
        for path in AGENTS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if self.registry.get(data["namespace"]):
                    continue
                agent = DynamicAgent(
                    namespace=data["namespace"],
                    description=data.get("description", ""),
                )
                for action_name, template in data.get("actions", {}).items():
                    agent.add_action(action_name, template)
                self.registry.register(agent)
                logger.info("Loaded saved agent: %s", data["namespace"])
            except Exception:
                logger.exception("Failed to load agent from %s", path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _reply(self, payload: AgentPayload, status: NotificationStatus,
               message: str) -> Notification:
        return Notification(
            task_id=payload.task_id,
            command_id=payload.command_id,
            status=status,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
            message=message,
        )

    @staticmethod
    def _is_admin(payload: AgentPayload) -> bool:
        """Check if the requesting user is an admin."""
        if not ADMIN_USER_IDS:
            return True  # Open mode — no restrictions
        user_id = payload.context.get("user_id", "")
        return user_id in ADMIN_USER_IDS

    @staticmethod
    def _help_text() -> str:
        return (
            "Agent Manager Commands:\n\n"
            '/agent_manager create my_bot "A helpful bot"\n'
            '/agent_manager add_action my_bot:greet "Hello {query}!"\n'
            '/agent_manager add_action my_bot:joke "Why did {query} cross the road?"\n'
            "/agent_manager list\n"
            "/agent_manager info my_bot\n"
            "/agent_manager remove_action my_bot:greet\n"
            "/agent_manager delete my_bot\n\n"
            "Then use your agent:\n"
            '/my_bot greet "World"'
        )
