# Multi-Agent Messaging & Orchestration POC

A namespace-routed messaging pipeline that decouples front-end channels (Telegram, Slack, Webhooks) from backend autonomous agents. One entry point routes commands to specialized agents and delivers async responses back to users.

## What Makes This Unique

Most frameworks solve one problem — LangChain does LLM orchestration, Slack Bolt does channel integration. This system does both, and adds runtime agent creation from chat:

- **Channel-agnostic + agent-agnostic** in a single pipeline
- **Create agents from Telegram** — no code deployment needed
- **Agent-to-Agent (A2A) communication** through the same orchestrator users interact with
- **LLM agents, template agents, and dynamic agents** all share the same registry and routing

## Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Telegram   │   │    Slack     │   │   Webhook    │
│   Adapter    │   │   Adapter    │   │   Adapter    │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │ Command
                          ▼
                ┌───────────────────┐
                │ Messaging Service │
                └────────┬──────────┘
                         │
                         ▼
                ┌───────────────────┐
                │   Orchestrator    │──── A2A calls ────┐
                │  (namespace       │                   │
                │   routing)        │◄──────────────────┘
                └────────┬──────────┘
                         │ AgentPayload
                         ▼
                ┌───────────────────┐
                │  Agent Registry   │
                │                   │
                │  ┌─────────────┐  │
                │  │ claude_agent│  │
                │  │ research    │  │
                │  │ agent_mgr   │  │
                │  │ (dynamic…)  │  │
                │  └─────────────┘  │
                └───────────────────┘
                         │
                         ▼ Notification
                 (back through adapter
                  to the user)
```

## Quick Start

### GitHub Codespaces (recommended)

1. Add secrets in GitHub (Settings → Codespaces → Secrets):
   - `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
   - `ANTHROPIC_API_KEY` — from [Anthropic Console](https://console.anthropic.com/)
2. Open the repo on GitHub, click **Code → Codespaces → Create codespace**
3. Create `.env` from your secrets:
   ```bash
   echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" > .env
   echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> .env
   ```
4. Run:
   ```bash
   python src/telegram_poll.py
   ```

### Local (Windows PowerShell)

```powershell
git clone https://github.com/jeff0926/AI-messaging-dervis.git
cd AI-messaging-dervis
git checkout claude/check-system-status-HhGZk
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

For Telegram polling (no public URL needed):
```powershell
python src/telegram_poll.py
```

### Local (Mac/Linux)

```bash
git clone https://github.com/jeff0926/AI-messaging-dervis.git
cd AI-messaging-dervis
git checkout claude/check-system-status-HhGZk
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens
python src/telegram_poll.py
```

### Docker

```bash
cp .env.example .env
# Edit .env with your tokens
docker-compose up --build
```

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes (for Telegram) | Token from [@BotFather](https://t.me/BotFather) |
| `ANTHROPIC_API_KEY` | Yes (for Claude agent) | Key from [Anthropic Console](https://console.anthropic.com/) |
| `SLACK_BOT_TOKEN` | No | Slack Bot OAuth token |
| `SLACK_SIGNING_SECRET` | No | Slack app signing secret |
| `API_KEY` | No | API key for webhook auth |
| `HOST` | No | Server bind host (default: `0.0.0.0`) |
| `PORT` | No | Server bind port (default: `8000`) |

## Built-in Agents

### claude_agent — AI-Powered Assistant

Uses the Claude API for intelligent responses.

| Action | Use Case | Example |
|---|---|---|
| `ask` | General Q&A — get clear answers on any topic | `/claude_agent ask "What causes inflation?"` |
| `code` | Code generation — get working code with explanations | `/claude_agent code "Write a Python function to merge two sorted lists"` |
| `summarize` | Condense long text into key bullet points | `/claude_agent summarize "Paste a long article or paragraph here"` |
| `analyze` | Deep analysis — multiple perspectives with evidence | `/claude_agent analyze "Impact of remote work on productivity"` |

### research_agent — Autonomous Research

Template-based research and summarization agent.

| Action | Use Case | Example |
|---|---|---|
| `run_autonomous_research` | Kick off a full research task on any topic | `/research_agent run_autonomous_research "Quantum Computing"` |
| `summarize` | Quick summary of provided text | `/research_agent summarize "Your text here"` |

### agent_manager — Create & Manage Agents from Chat

Spin up new agents, add actions, and manage them — all from Telegram. No code required.

| Action | Use Case | Example |
|---|---|---|
| `create` | Spin up a new custom agent on the fly | `/agent_manager create my_bot "A helpful bot"` |
| `add_action` | Teach your agent a new command with a response template | `/agent_manager add_action my_bot:greet "Hello {query}!"` |
| `list` | See all agents and their available commands | `/agent_manager list` |
| `info` | See details about a specific agent | `/agent_manager info my_bot` |
| `remove_action` | Remove a command from a custom agent | `/agent_manager remove_action my_bot:greet` |
| `delete` | Delete a custom agent entirely | `/agent_manager delete my_bot` |
| `help` | Show agent manager usage guide | `/agent_manager help` |

**Example: Create a bot in 30 seconds from Telegram:**
```
/agent_manager create my_bot "My first custom bot"
/agent_manager add_action my_bot:greet "Hello {query}! Welcome aboard."
/agent_manager add_action my_bot:joke "Why did {query} cross the road? To get to the other side!"
/my_bot greet "World"           → "Hello World! Welcome aboard."
/my_bot joke "the chicken"      → "Why did the chicken cross the road? To get to the other side!"
```

Custom agents persist to `data/agents/` as JSON and survive restarts.

### Telegram Quick Commands

| Command | What it does |
|---|---|
| `/help` | Show all agents with examples and use cases |
| `/start` | Same as /help |
| `/agent_manager list` | List all agents and their actions |

## Agent-to-Agent (A2A) Communication

Agents can call other agents through the orchestrator. Any agent with an orchestrator reference can do:

```python
result = await self.call_agent(
    target_namespace="claude_agent",
    action="summarize",
    parameters={"query": "Text to summarize"},
    parent_payload=payload,  # preserves context chain
)
```

The orchestrator logs all A2A calls and handles errors, so agents can safely compose complex workflows by delegating subtasks.

## Webhook API

```bash
# Health check
curl http://localhost:8000/health

# List all agents and capabilities
curl http://localhost:8000/agents

# Send a command
curl -X POST http://localhost:8000/webhook/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"user_id":"test","namespace":"claude_agent","action":"ask","parameters":{"query":"What is AI?"}}'

# Check background tasks
curl http://localhost:8000/tasks
curl http://localhost:8000/tasks/{task_id}
```

### Authentication

Set `AUTH_ENABLED=true` and `API_KEY=your-secret` in `.env`. Protected endpoints require an `X-API-Key` header. Public paths (`/health`, `/agents`) and channel webhooks (Telegram, Slack) are excluded.

### Slack Integration

1. Create a Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes: `chat:write`, `commands`
3. Set the request URL to `http://your-host:8000/webhook/slack`
4. Add `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` to `.env`

Commands work the same way across all channels:
```
/research_agent run_autonomous_research "Quantum Computing"
```

## Project Structure

```
src/
├── schemas/                   # Data models (Pydantic v2)
│   ├── command.py             # Incoming request from any channel
│   ├── agent_payload.py       # Orchestrator → Agent payload
│   └── notification.py        # Agent → User response
├── agents/
│   ├── base.py                # BaseAgent abstract class + A2A call_agent()
│   ├── registry.py            # Namespace → Agent lookup + orchestrator wiring
│   ├── research_agent.py      # Research agent (template-based)
│   ├── claude_agent.py        # Claude API-powered LLM agent
│   ├── dynamic_agent.py       # Runtime-created agents with template responses
│   └── agent_manager.py       # CRUD agents from Telegram chat
├── adapters/
│   ├── base.py                # BaseChannelAdapter abstract class
│   ├── telegram.py            # Telegram Bot API (parse + send)
│   ├── webhook.py             # Generic JSON webhook (pass-through)
│   └── slack.py               # Slack Events API + slash commands
├── services/
│   ├── orchestrator.py        # Namespace routing + A2A dispatch
│   ├── messaging.py           # Adapter ↔ Orchestrator bridge
│   └── task_queue.py          # Async background task runner
├── middleware/
│   └── auth.py                # API key authentication
├── app.py                     # FastAPI server (webhook mode)
└── telegram_poll.py           # Telegram polling (no ngrok needed)
tests/                         # 28 tests covering all components
config/
data/agents/                   # Persisted dynamic agents (JSON)
```

## Data Flow

### Three schemas drive the entire pipeline:

| Schema | Purpose | Fields |
|---|---|---|
| **Command** | Incoming user request (channel-agnostic) | user_id, namespace, action, parameters, metadata |
| **AgentPayload** | What the orchestrator sends to an agent | task_id, command_id, payload, context |
| **Notification** | What agents send back to the user | status, message, media, data, transformation_hints |

### Request lifecycle:

1. User sends `/claude_agent ask "What is AI?"` on Telegram
2. **TelegramAdapter.parse_incoming()** → `Command(namespace="claude_agent", action="ask")`
3. **MessagingService.handle_incoming()** → passes to Orchestrator
4. **Orchestrator.dispatch()** → looks up `claude_agent` in Registry → calls `agent.handle()`
5. **ClaudeAgent.handle()** → calls Anthropic API → returns `Notification(status=completed)`
6. **TelegramAdapter.send_notification()** → formats and sends reply via Telegram API

## Adding a New Agent

### Option 1: From Telegram (no code)

```
/agent_manager create weather_bot "Reports weather for any city"
/agent_manager add_action weather_bot:forecast "The forecast for {query} is sunny with a high of 72F"
/weather_bot forecast "San Francisco"
```

### Option 2: In code (for real logic)

Create `src/agents/my_agent.py`:

```python
from src.agents.base import BaseAgent
from src.schemas import AgentPayload, Notification, NotificationStatus

class MyAgent(BaseAgent):
    namespace = "my_agent"

    async def handle(self, payload: AgentPayload) -> Notification:
        action = getattr(self, f"action_{payload.action}", None)
        if not action:
            return Notification(
                task_id=payload.task_id, command_id=payload.command_id,
                status=NotificationStatus.FAILED,
                target_channel=payload.context.get("source_channel", "unknown"),
                target_user_id=payload.context.get("user_id", "unknown"),
                message=f"Unknown action: {payload.action}",
            )
        return await action(payload)

    async def action_hello(self, payload: AgentPayload) -> Notification:
        name = payload.payload.get("query", "World")

        # Example: call another agent
        summary = await self.call_agent(
            "claude_agent", "summarize",
            parameters={"query": f"Brief intro about {name}"},
            parent_payload=payload,
        )

        return Notification(
            task_id=payload.task_id, command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
            message=f"Hello, {name}!\n\n{summary.message}",
        )
```

Register in `src/telegram_poll.py` or `src/app.py`:

```python
from src.agents.my_agent import MyAgent
registry.register(MyAgent())
```

## Adding a New Channel Adapter

Implement `BaseChannelAdapter`:

```python
from src.adapters.base import BaseChannelAdapter
from src.schemas import Command, Notification

class DiscordAdapter(BaseChannelAdapter):
    channel_name = "discord"

    async def parse_incoming(self, raw: dict) -> Command:
        # Transform Discord payload → Command
        ...

    async def send_notification(self, notification: Notification) -> None:
        # Transform Notification → Discord message and send
        ...
```

Register in `src/app.py`:

```python
messaging.register_adapter(DiscordAdapter(token="..."))
```

## Running Tests

```bash
python -m pytest tests/ -v
```

28 tests covering schemas, registry, pipeline, Telegram adapter, A2A communication, auth middleware, and async task queue.

## License

MIT
