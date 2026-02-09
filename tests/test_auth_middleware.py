"""Tests for the API key auth middleware."""

import os

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.middleware.auth import ApiKeyMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(ApiKeyMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/webhook/test")
    async def webhook():
        return {"result": "ok"}

    @app.post("/telegram/webhook")
    async def telegram():
        return {"result": "ok"}

    return app


def test_auth_disabled_allows_all(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    client = TestClient(_make_app())
    resp = client.post("/webhook/test", json={})
    assert resp.status_code == 200


def test_auth_enabled_rejects_without_key(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    client = TestClient(_make_app())
    resp = client.post("/webhook/test", json={})
    assert resp.status_code == 401


def test_auth_enabled_accepts_correct_key(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    client = TestClient(_make_app())
    resp = client.post(
        "/webhook/test", json={},
        headers={"X-API-Key": "secret123"},
    )
    assert resp.status_code == 200


def test_auth_skips_public_paths(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    client = TestClient(_make_app())
    resp = client.get("/health")
    assert resp.status_code == 200


def test_auth_skips_telegram_webhook(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    client = TestClient(_make_app())
    resp = client.post("/telegram/webhook", json={})
    assert resp.status_code == 200
