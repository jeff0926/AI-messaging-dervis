"""Catalog Manager — browse, save, and manage reusable functions from Telegram."""

from __future__ import annotations

import logging
import os
import textwrap

from src.agents.base import BaseAgent
from src.agents.agent_manager import ADMIN_USER_IDS, _PUBLIC_ACTIONS as _AM_PUBLIC
from src.schemas import AgentPayload, Notification, NotificationStatus
from src.services.function_catalog import FunctionCatalog, FunctionEntry

logger = logging.getLogger(__name__)

# Read-only actions anyone can use
_PUBLIC_ACTIONS = {"list", "info", "search", "help"}


class CatalogManager(BaseAgent):
    """Agent that manages the Function Catalog via Telegram commands.

    Namespace: ``catalog``

    Write operations (save, delete, tag) are restricted to admins
    when ADMIN_USER_IDS is set. Read operations are always public.
    """

    namespace = "catalog"

    def __init__(self, catalog: FunctionCatalog | None = None) -> None:
        self.catalog = catalog or FunctionCatalog()

    def capabilities(self) -> list[str]:
        return ["save", "list", "info", "search", "delete", "tag", "help"]

    async def handle(self, payload: AgentPayload) -> Notification:
        action = payload.action
        query = payload.payload.get("query", "")

        handler = {
            "save": self._save,
            "list": self._list,
            "info": self._info,
            "search": self._search,
            "delete": self._delete,
            "tag": self._tag,
            "help": self._help,
        }.get(action)

        if handler is None:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"Unknown command: {action}\n\n{self._help_text()}",
            )

        # Admin check for write operations
        if action not in _PUBLIC_ACTIONS and not self._is_admin(payload):
            return self._reply(
                payload, NotificationStatus.FAILED,
                "Permission denied. Only admins can save/delete/tag functions.\n"
                "Contact the bot owner to be added to ADMIN_USER_IDS.",
            )

        return handler(payload, query)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _save(self, payload: AgentPayload, query: str) -> Notification:
        """Save a function to the catalog.

        Format: /catalog save func_name "Description" ```source code```
        Minimal: /catalog save func_name "Description"
        """
        # Parse: func_name "description" ```optional source```
        parts = query.split(None, 1)
        name = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if not name:
            return self._reply(
                payload, NotificationStatus.FAILED,
                'Usage: /catalog save func_name "Description of what it does"',
            )

        # Extract description (in quotes) and optional source (in backticks)
        description = ""
        source = ""

        if '"' in rest:
            # Extract quoted description
            start = rest.index('"') + 1
            end = rest.index('"', start) if '"' in rest[start:] else len(rest)
            description = rest[start:end]
            rest = rest[end + 1:].strip() if end < len(rest) else ""
        else:
            description = rest.strip()
            rest = ""

        # Extract optional source code between ``` markers
        if "```" in rest:
            code_start = rest.index("```") + 3
            # Skip optional language identifier on same line
            newline = rest.find("\n", code_start)
            if newline != -1 and newline - code_start < 20:
                code_start = newline + 1
            code_end = rest.index("```", code_start) if "```" in rest[code_start:] else len(rest)
            source = rest[code_start:code_end].strip()

        user_id = payload.context.get("user_id", "unknown")
        existing = self.catalog.get(name)

        entry = FunctionEntry(
            name=name,
            description=description,
            source=source,
            created_by=user_id,
        )
        self.catalog.save(entry)

        verb = "updated" if existing else "saved"
        msg = f"Function '{name}' {verb} to catalog.\n\n"
        msg += f"Description: {description}\n"
        if source:
            msg += f"Source: {len(source)} chars\n"
        msg += f"\nView it: /catalog info {name}"

        return self._reply(payload, NotificationStatus.COMPLETED, msg)

    def _list(self, payload: AgentPayload, query: str) -> Notification:
        """List all functions in the catalog."""
        entries = self.catalog.list_all()
        if not entries:
            return self._reply(
                payload, NotificationStatus.COMPLETED,
                "Function catalog is empty.\n\n"
                'Save your first function:\n'
                '/catalog save my_func "Description of what it does"',
            )

        lines = [f"Function Catalog ({len(entries)} functions):\n"]
        for entry in entries:
            lines.append(f"  {entry.summary()}")
        lines.append(f"\nView details: /catalog info <name>")
        lines.append(f"Search: /catalog search <keyword>")

        return self._reply(
            payload, NotificationStatus.COMPLETED, "\n".join(lines),
        )

    def _info(self, payload: AgentPayload, query: str) -> Notification:
        """Show details about a specific function."""
        name = query.strip()
        if not name:
            return self._reply(
                payload, NotificationStatus.FAILED,
                "Usage: /catalog info func_name",
            )

        entry = self.catalog.get(name)
        if not entry:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"No function named '{name}' in catalog.\n"
                f"Use /catalog list to see all functions.",
            )

        lines = [
            f"Function: {entry.name}",
            f"Description: {entry.description}",
            f"Parameters: {_fmt_schema(entry.parameters)}",
            f"Returns: {_fmt_schema(entry.returns)}",
        ]
        if entry.tags:
            lines.append(f"Tags: {', '.join(entry.tags)}")
        lines.append(f"Created by: {entry.created_by}")
        lines.append(f"Created at: {entry.created_at}")
        if entry.source:
            # Truncate for Telegram display
            src_preview = entry.source[:500]
            if len(entry.source) > 500:
                src_preview += "\n... (truncated)"
            lines.append(f"\nSource:\n```\n{src_preview}\n```")

        return self._reply(
            payload, NotificationStatus.COMPLETED, "\n".join(lines),
        )

    def _search(self, payload: AgentPayload, query: str) -> Notification:
        """Search the catalog by keyword."""
        keyword = query.strip()
        if not keyword:
            return self._reply(
                payload, NotificationStatus.FAILED,
                "Usage: /catalog search <keyword>",
            )

        results = self.catalog.search(keyword)
        if not results:
            return self._reply(
                payload, NotificationStatus.COMPLETED,
                f"No functions matching '{keyword}'.\n"
                f"Use /catalog list to see all functions.",
            )

        lines = [f"Search results for '{keyword}' ({len(results)} found):\n"]
        for entry in results:
            lines.append(f"  {entry.summary()}")

        return self._reply(
            payload, NotificationStatus.COMPLETED, "\n".join(lines),
        )

    def _delete(self, payload: AgentPayload, query: str) -> Notification:
        """Remove a function from the catalog."""
        name = query.strip()
        if not name:
            return self._reply(
                payload, NotificationStatus.FAILED,
                "Usage: /catalog delete func_name",
            )

        if self.catalog.delete(name):
            return self._reply(
                payload, NotificationStatus.COMPLETED,
                f"Function '{name}' deleted from catalog.",
            )
        return self._reply(
            payload, NotificationStatus.FAILED,
            f"No function named '{name}' in catalog.",
        )

    def _tag(self, payload: AgentPayload, query: str) -> Notification:
        """Add tags to a function. Format: func_name tag1 tag2 tag3"""
        parts = query.split()
        name = parts[0] if parts else ""
        tags = parts[1:] if len(parts) > 1 else []

        if not name or not tags:
            return self._reply(
                payload, NotificationStatus.FAILED,
                "Usage: /catalog tag func_name tag1 tag2 tag3",
            )

        entry = self.catalog.get(name)
        if not entry:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"No function named '{name}' in catalog.",
            )

        # Add new tags (no duplicates)
        existing = set(entry.tags)
        for t in tags:
            if t not in existing:
                entry.tags.append(t)
                existing.add(t)
        self.catalog.save(entry)

        return self._reply(
            payload, NotificationStatus.COMPLETED,
            f"Tags updated for '{name}': {', '.join(entry.tags)}",
        )

    def _help(self, payload: AgentPayload, query: str) -> Notification:
        return self._reply(
            payload, NotificationStatus.COMPLETED, self._help_text(),
        )

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
        if not ADMIN_USER_IDS:
            return True
        user_id = payload.context.get("user_id", "")
        return user_id in ADMIN_USER_IDS

    @staticmethod
    def _help_text() -> str:
        return (
            "Function Catalog Commands:\n\n"
            "Browse:\n"
            "  /catalog list — see all functions\n"
            "  /catalog info func_name — function details\n"
            "  /catalog search keyword — search by name/description/tag\n\n"
            "Manage:\n"
            '  /catalog save func_name "Description" — save a function\n'
            "  /catalog tag func_name research trending — add tags\n"
            "  /catalog delete func_name — remove a function\n\n"
            "Example:\n"
            '  /catalog save find_trending "Search trending topics for a subject"\n'
            "  /catalog tag find_trending research trends social\n"
            "  /catalog info find_trending"
        )


def _fmt_schema(schema: dict) -> str:
    """Format a parameter/return schema for display."""
    return ", ".join(f"{k}: {v}" for k, v in schema.items())
