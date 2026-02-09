"""Claude Agent — LLM-powered agent using the Anthropic API."""

from __future__ import annotations

import logging
import os

import httpx

from src.agents.base import BaseAgent
from src.schemas import AgentPayload, Notification, NotificationStatus

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 1024


class ClaudeAgent(BaseAgent):
    """Agent that forwards queries to the Claude API.

    Namespace: ``claude_agent``

    Actions:
        - ask: general question answering
        - code: code generation / explanation
        - summarize: summarize provided text
        - analyze: deeper analysis of a topic
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
        return list(self.ACTIONS.keys())

    async def handle(self, payload: AgentPayload) -> Notification:
        if not self.api_key:
            return self._reply(
                payload, NotificationStatus.FAILED,
                "ANTHROPIC_API_KEY not configured. Add it to your .env file.",
            )

        action = payload.action
        query = payload.payload.get("query", "")

        if not query:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"No query provided. Usage: /claude_agent {action} \"your question\"",
            )

        system_prompts = self.ACTIONS

        system = system_prompts.get(action)
        if system is None:
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"Unknown action: {action}\n"
                f"Available: {list(system_prompts.keys())}",
            )

        try:
            response_text = await self._call_claude(system, query)
        except Exception as exc:
            logger.exception("Claude API call failed")
            return self._reply(
                payload, NotificationStatus.FAILED,
                f"Claude API error: {exc}",
            )

        return self._reply(payload, NotificationStatus.COMPLETED, response_text)

    async def _call_claude(self, system: str, user_message: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user_message}],
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
