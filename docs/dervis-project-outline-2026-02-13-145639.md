# Dervis — Multi-Agent Messaging & Orchestration Platform

**Project Outline — 2026-02-13**

---

## What Is Dervis?

A namespace-routed messaging pipeline that decouples front-end channels (Telegram, Slack, Webhooks) from backend autonomous agents. Users interact with specialized AI agents through any supported channel using a unified command syntax. Agents can be created, configured, and composed entirely from chat — no code deployment required.

---

## Current Status

### Phase: POC — Functional & Live on Telegram

| Component | Status | Notes |
|---|---|---|
| Core Pipeline (schemas, orchestrator, registry) | Done | 3-schema pipeline: Command → AgentPayload → Notification |
| Telegram Adapter (polling mode) | Done | Live, tested, no ngrok needed |
| Slack Adapter | Done | Events API + slash commands + signature verification |
| Webhook Adapter | Done | Generic JSON pass-through for any HTTP client |
| Research Agent | Done | Template-based research and summarization |
| Claude Agent | Done | Claude API with per-user conversation memory (last 20 msgs) |
| Agent Manager | Done | Create/delete/configure agents from Telegram chat |
| Function Catalog | Done | Save, browse, search, tag reusable function definitions |
| Dynamic Agents | Done | Runtime-created agents with template responses, persisted as JSON |
| Admin Security | Done | ADMIN_USER_IDS env var gates write operations |
| A2A Communication | Done | Agent-to-agent calls through orchestrator with depth guard (max 5) |
| @action Decorator | Done | Declarative action authoring with metadata |
| Auth Middleware | Done | API key authentication for webhook endpoints |
| Task Queue | Done | Async background task runner with status tracking |
| Docker | Done | Containerized deployment with docker-compose |
| GitHub Codespaces | Done | One-click cloud launch with devcontainer config |
| Tests | 81 passing | Full coverage across all components |

### Deployment

- **Primary**: GitHub Codespaces (cloud)
- **Secondary**: Local Windows PowerShell, Mac/Linux, Docker
- **Bot**: @JC_zbot on Telegram

### Environment

- Python 3.11
- FastAPI + Pydantic v2
- httpx for async HTTP
- Anthropic Claude API for LLM agent
- GitHub Codespaces secrets for credentials

---

## Goals

### Completed

1. Channel-agnostic messaging pipeline with namespace routing
2. Multiple channel adapters (Telegram, Slack, Webhook)
3. Agent registry with dynamic discovery
4. Runtime agent creation from Telegram chat
5. Claude-powered AI agent with conversation memory
6. Function Catalog for reusable building blocks
7. Admin security for production readiness
8. A2A communication with infinite loop protection
9. Comprehensive test suite (81 tests)

### In Progress / Next

| Goal | Priority | Description |
|---|---|---|
| Function Sandbox | High | Safe execution environment for user-generated Python (RestrictedPython or Docker isolation) |
| Agent Composition | High | Attach catalog functions to agents (`/agent_manager attach bot:action func_name`) |
| NL Interpreter | Medium | Natural language → structured commands. Replace `/namespace action` with free-form text |
| Plan-Approve-Build Loop | Medium | System decomposes NL requests, does catalog gap analysis, proposes plan, user approves, system builds |
| Telegram Voice Support | Low | Voice-to-text → NL interpreter pipeline |
| Redis/DB Persistence | Low | Swap in-memory conversation store for durable storage |

### Long Vision

A self-building agent platform where users:
1. Describe what they need in plain English (voice or text) on Telegram
2. System decomposes the request into modular functions
3. Checks the catalog — identifies what exists vs what needs to be built
4. Proposes a plan: "I need 3 functions, 1 exists, 2 need to be built. Shall I proceed?"
5. User approves
6. System builds missing functions, tests in sandbox, catalogs them
7. Composes functions into a working agent
8. Agent is live and usable immediately

---

## Unique Benefits

### 1. Chat-First Agent Factory
No other platform lets you create, configure, and compose agents entirely from a messaging app. Zero deployment, zero code for end users.

### 2. Channel-Agnostic + Agent-Agnostic
Most frameworks solve one side — LangChain does LLM orchestration, Slack Bolt does channel integration. Dervis does both in a single pipeline. Add a new channel or a new agent without touching the other.

### 3. Function Catalog as a Building Block Library
Reusable, tagged, searchable function definitions that can be composed into agents. Like npm for agent capabilities — build once, reuse everywhere.

### 4. Agent-to-Agent Communication
Agents call other agents through the same orchestrator users interact with. Depth-limited to prevent infinite loops. Enables multi-agent workflows without custom wiring.

### 5. Self-Extending Platform (future)
The NL interpreter + catalog gap analysis + plan-approve-build loop means the platform gets more capable with every user interaction. Each new function enriches the catalog for all future agents.

### 6. Runtime Composability
Three ways to create agents (from chat, with @action decorator, with action_* convention) and runtime function attachment means agents can be assembled from parts without redeployment.

---

## Architecture at a Glance

```
Telegram / Slack / Webhook
        ↓
   Messaging Service
        ↓
    Orchestrator ←→ Agent Registry
        ↓                ↓
   Agent Dispatch    A2A Calls
        ↓
  ┌─────────────────────────────────┐
  │ claude_agent (LLM + memory)     │
  │ research_agent (templates)      │
  │ agent_manager (CRUD from chat)  │
  │ catalog (function library)      │
  │ dynamic agents (user-created)   │
  └─────────────────────────────────┘
        ↓
    Notification → Channel Adapter → User
```

---

## Key Files

| File | Purpose |
|---|---|
| `src/services/orchestrator.py` | Central routing + A2A dispatch + depth guard |
| `src/agents/base.py` | Agent ABC + action discovery + A2A call_agent() |
| `src/agents/registry.py` | Namespace → Agent lookup |
| `src/agents/claude_agent.py` | Claude API agent with conversation memory |
| `src/agents/agent_manager.py` | CRUD agents from chat + admin security |
| `src/agents/catalog_manager.py` | Function catalog management from chat |
| `src/services/function_catalog.py` | Persistent function store (JSON) |
| `src/services/conversation.py` | Per-user conversation memory |
| `src/agents/decorators.py` | @action decorator for declarative authoring |
| `src/adapters/telegram.py` | Telegram Bot API adapter |
| `src/telegram_poll.py` | Telegram polling mode + /help + ACTION_GUIDE |
| `src/app.py` | FastAPI server (webhook mode) |

---

## Repo & Credentials

- **Repo**: github.com/jeff0926/AI-messaging-dervis
- **Branch**: `claude/check-system-status-HhGZk`
- **Bot**: @JC_zbot (Telegram)
- **Secrets**: TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, ADMIN_USER_IDS (in Codespace secrets + .env)

---

*Last updated: 2026-02-13*
