"""API key authentication middleware for webhook endpoints."""

from __future__ import annotations

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths that don't require authentication
PUBLIC_PATHS = {"/health", "/agents", "/docs", "/openapi.json", "/redoc"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on protected endpoints.

    Enable by setting AUTH_ENABLED=true and API_KEY=<your-key> in .env.
    Telegram and Slack webhooks are excluded (they have their own auth).
    """

    async def dispatch(self, request: Request, call_next):
        auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
        if not auth_enabled:
            return await call_next(request)

        path = request.url.path

        # Skip auth for public paths
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for Telegram/Slack webhooks (they verify via their own tokens)
        if path.startswith("/telegram/") or path.endswith("/slack"):
            return await call_next(request)

        # Check API key
        expected_key = os.getenv("API_KEY", "")
        if not expected_key:
            logger.warning("AUTH_ENABLED=true but API_KEY is empty")
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key", "")
        if provided_key != expected_key:
            logger.warning("Rejected request to %s — invalid API key", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
