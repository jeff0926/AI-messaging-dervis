"""Research Agent — example agent that demonstrates the namespace/action contract."""

from __future__ import annotations

import asyncio
import logging

from src.agents.base import BaseAgent
from src.schemas import AgentPayload, Notification, NotificationStatus

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Demonstrates a fully wired agent.

    Namespace: ``research_agent``
    Supported actions:
        - run_autonomous_research
        - summarize
    """

    namespace = "research_agent"

    async def handle(self, payload: AgentPayload) -> Notification:
        action_method = getattr(self, f"action_{payload.action}", None)
        if action_method is None:
            return self._error(payload, f"Unknown action: {payload.action}")
        return await action_method(payload)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    async def action_run_autonomous_research(
        self, payload: AgentPayload
    ) -> Notification:
        query = payload.payload.get("query", "")
        logger.info("Research agent: starting research on '%s'", query)

        # Simulate async work (replace with real logic)
        await asyncio.sleep(0.1)

        return Notification(
            task_id=payload.task_id,
            command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
            message=f"Research complete for: *{query}*\n\n"
            "Here are the key findings:\n"
            "1. Topic overview gathered\n"
            "2. Key papers identified\n"
            "3. Summary compiled",
        )

    async def action_summarize(self, payload: AgentPayload) -> Notification:
        text = payload.payload.get("query", "")
        summary = text[:200] + ("…" if len(text) > 200 else "")
        return Notification(
            task_id=payload.task_id,
            command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            message=f"Summary: {summary}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _error(payload: AgentPayload, msg: str) -> Notification:
        return Notification(
            task_id=payload.task_id,
            command_id=payload.command_id,
            status=NotificationStatus.FAILED,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            message=msg,
        )
