"""Claude Agent — LLM-powered agent using the Anthropic API with conversation memory."""

from __future__ import annotations

import logging
import os

import httpx

from src.agents.base import BaseAgent
from src.agents.decorators import action
from src.schemas import AgentPayload, Notification, NotificationStatus
from src.services.conversation import conversation_store

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 1024


class ClaudeAgent(BaseAgent):
    """Agent that forwards queries to the Claude API with conversation memory.

    Namespace: ``claude_agent``

    The ``ask`` action maintains per-user conversation history so Claude
    remembers context across messages. Use ``clear`` to reset.
    """

    namespace = "claude_agent"

    ACTIONS = {
        "ask": "You are a helpful assistant. Answer clearly and concisely.",
        "code": (
            "You are an expert programmer. Provide clean, well-commented code. "
            "Use markdown code blocks with language tags."
        ),
        "summarize": (
            "Summarize the following text clearly and concisely. "
            "Use bullet points for key takeaways."
        ),
        "analyze": (
            "You are a research analyst. Provide a thorough analysis with "
            "multiple perspectives, evidence, and a clear conclusion."
        ),
    }

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model

    def capabilities(self) -> list[str]:
        return list(self.ACTIONS.keys()) + ["clear"]

    async def handle(self, payload: AgentPayload) -> Notification:
        if payload.action == "clear":
            return await self._clear_history(payload)

        if not self.api_key:
            return self._reply(
                payload, NotificationStatus.FAILED,
                "ANTHROPIC_API_KEY not configured. Add it to your .env file.",
            )

        act = payload.action
        query = payload.payload.get("query", "")

        if not query:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"No query provided. Usage: /claude_agent {act} \"your question\"",
            )

        system = self.ACTIONS.get(act)
        if system is None:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"Unknown action: {act}\n"
                f"Available: {self.capabilities()}",
            )

        user_id = payload.context.get("user_id", "unknown")
        channel = payload.context.get("source_channel", "")

        # Build message history for the ask action (conversational memory)
        if act == "ask":
            conversation_store.add_user_message(user_id, query, channel)
            messages = conversation_store.get_history(user_id, channel)
        else:
            # Non-conversational actions: single message, no history
            messages = [{"role": "user", "content": query}]

        try:
            response_text = await self._call_claude(system, messages)
        except Exception as exc:
            logger.exception("Claude API call failed")
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"Claude API error: {exc}",
            )

        # Save assistant response to history for ask action
        if act == "ask":
            conversation_store.add_assistant_message(user_id, response_text, channel)

        return self._reply(payload, NotificationStatus.COMPLETED, response_text)

    async def _clear_history(self, payload: AgentPayload) -> Notification:
        user_id = payload.context.get("user_id", "unknown")
        channel = payload.context.get("source_channel", "")
        conversation_store.clear(user_id, channel)
        return self._reply(
            payload, NotificationStatus.COMPLETED,
            "Conversation history cleared. Starting fresh.",
        )

    async def _call_claude(
        self, system: str, messages: list[dict[str, str]]
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(ANTHROPIC_API_URL, headers=headers, json=body)

            if resp.status_code != 200:
                error = resp.json().get("error", {}).get("message", resp.text)
                raise RuntimeError(f"API returned {resp.status_code}: {error}")

            data = resp.json()
            return data["content"][0]["text"]

    def _reply(
        self, payload: AgentPayload, status: NotificationStatus, message: str
    ) -> Notification:
        return Notification(
            task_id=payload.task_id,
            command_id=payload.command_id,
            status=status,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
            message=message,
        )
