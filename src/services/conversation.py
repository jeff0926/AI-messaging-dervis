"""Conversation memory — per-user message history for stateful agents."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MAX_HISTORY = 20  # messages per conversation


class ConversationStore:
    """In-memory conversation history keyed by (user_id, channel).

    Each conversation stores the last ``max_history`` messages as
    {"role": "user"|"assistant", "content": str} dicts — matching
    the Claude API message format.

    For production, swap this with Redis or a database.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self.max_history = max_history
        self._store: dict[str, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    def _key(self, user_id: str, channel: str = "") -> str:
        return f"{channel}:{user_id}"

    def add_user_message(self, user_id: str, content: str, channel: str = "") -> None:
        self._store[self._key(user_id, channel)].append(
            {"role": "user", "content": content}
        )

    def add_assistant_message(self, user_id: str, content: str, channel: str = "") -> None:
        self._store[self._key(user_id, channel)].append(
            {"role": "assistant", "content": content}
        )

    def get_history(self, user_id: str, channel: str = "") -> list[dict[str, str]]:
        """Return the conversation history as a list of messages."""
        return list(self._store[self._key(user_id, channel)])

    def clear(self, user_id: str, channel: str = "") -> None:
        """Clear conversation history for a user."""
        key = self._key(user_id, channel)
        self._store.pop(key, None)

    def clear_all(self) -> None:
        """Clear all conversations."""
        self._store.clear()

    def stats(self) -> dict[str, Any]:
        """Return stats about the conversation store."""
        return {
            "conversations": len(self._store),
            "total_messages": sum(len(v) for v in self._store.values()),
        }


# Singleton instance
conversation_store = ConversationStore()
