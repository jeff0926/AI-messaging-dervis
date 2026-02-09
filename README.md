# Multi-Agent Messaging & Orchestration POC

A namespace-routed messaging pipeline that decouples front-end channels (Telegram, Slack, Webhooks) from backend autonomous agents. One entry point routes commands to specialized agents and delivers async responses back to users.

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
                │   Orchestrator    │
                │  (namespace       │
                │   routing)        │
                └────────┬──────────┘
                         │ AgentPayload
                         ▼
                ┌───────────────────┐
                │  Agent Registry   │
                │                   │
                │  ┌─────────────┐  │
                │  │ research    │  │
                │  │ agent_mgr   │  │
                │  │ claude_agent│  │
                │  │ (dynamic…)  │  │
                │  └─────────────┘  │
                └───────────────────┘
                         │
                         ▼ Notification
                 (back through adapter
                  to the user)
```

## Quick Start

### Local (Windows PowerShell)

```powershell
git clone https://github.com/jeff0926/AI-messaging-dervis.git
cd AI-messaging-dervis
git checkout claude/check-system-status-HhGZk
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens
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

### GitHub Codespaces (recommended)

1. Add `TELEGRAM_BOT_TOKEN` as a Codespace secret (Settings → Codespaces → Secrets)
2. Open the repo on GitHub, click **Code → Codespaces → Create codespace**
3. Wait for auto-setup, then run:
   ```bash
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

## Usage

### Telegram Commands

**Built-in agents:**

```
/research_agent run_autonomous_research "Quantum Computing"
/research_agent summarize "Long text to summarize"
/claude_agent ask "Explain quantum entanglement"
/claude_agent code "Write a Python function to sort a list"
```

**Managing agents from chat:**

```
/agent_manager create my_bot "My custom bot"
/agent_manager add_action my_bot:greet "Hello {query}!"
/agent_manager add_action my_bot:joke "Why did {query} cross the road?"
/agent_manager list
/agent_manager info my_bot
/agent_manager remove_action my_bot:joke
/agent_manager delete my_bot
```

**Using custom agents:**

```
/my_bot greet "World"
/my_bot joke "the chicken"
```

### Webhook API

```bash
# Health check
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/agents

# Send a command (with auth)
curl -X POST http://localhost:8000/webhook/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"user_id":"test","namespace":"research_agent","action":"run_autonomous_research","parameters":{"query":"Quantum Computing"}}'
```

### Slack

1. Create a Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes: `chat:write`, `commands`
3. Set the request URL to `http://your-host:8000/webhook/slack`
4. Add `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` to `.env`

Use the same namespace:action pattern:
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
│   ├── base.py                # BaseAgent abstract class
│   ├── registry.py            # Namespace → Agent lookup
│   ├── research_agent.py      # Research agent (template)
│   ├── claude_agent.py        # Claude API-powered agent
│   ├── dynamic_agent.py       # Runtime-created agents
│   └── agent_manager.py       # CRUD agents from Telegram
├── adapters/
│   ├── base.py                # BaseChannelAdapter abstract class
│   ├── telegram.py            # Telegram Bot API adapter
│   ├── webhook.py             # Generic JSON webhook adapter
│   └── slack.py               # Slack adapter
├── services/
│   ├── orchestrator.py        # Namespace routing engine
│   ├── messaging.py           # Adapter ↔ Orchestrator bridge
│   └── task_queue.py          # Async task queue
├── middleware/
│   └── auth.py                # API key authentication
├── app.py                     # FastAPI server (webhook mode)
└── telegram_poll.py           # Telegram polling (no ngrok)
tests/
config/
data/agents/                   # Persisted dynamic agents (JSON)
```

## Data Flow

### Three schemas drive the entire pipeline:

| Schema | Purpose | Example |
|---|---|---|
| **Command** | Incoming user request (channel-agnostic) | user_id, namespace, action, parameters |
| **AgentPayload** | What the orchestrator sends to an agent | task_id, payload, context |
| **Notification** | What agents send back to the user | status, message, media, data |

### Request lifecycle:

1. User sends `/research_agent run_autonomous_research "AI"` on Telegram
2. **TelegramAdapter.parse_incoming()** → `Command(namespace="research_agent", action="run_autonomous_research")`
3. **MessagingService.handle_incoming()** → passes to Orchestrator
4. **Orchestrator.dispatch()** → looks up `research_agent` in Registry → calls `agent.handle()`
5. **Agent.handle()** → does work → returns `Notification(status=completed, message="...")`
6. **TelegramAdapter.send_notification()** → formats and sends reply via Telegram API

## Adding a New Agent

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
        return Notification(
            task_id=payload.task_id, command_id=payload.command_id,
            status=NotificationStatus.COMPLETED,
            target_channel=payload.context.get("source_channel", "unknown"),
            target_user_id=payload.context.get("user_id", "unknown"),
            data={"chat_id": payload.context.get("metadata", {}).get("chat_id")},
            message=f"Hello, {name}!",
        )
```

Register it in `src/app.py` or `src/telegram_poll.py`:

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

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
