# CrewAI Multi-Agent Email Triage with Scalekit

A multi-agent CrewAI crew that triages a Gmail inbox using Scalekit-authenticated tools. Three agents collaborate in sequence: one scans unread emails, another classifies them by priority, and a third drafts replies for the high-priority items.

## What it does

- **Inbox Scanner** — fetches the latest unread emails via Gmail tools and extracts metadata (subject, sender, date, preview)
- **Prioritizer** — classifies each email as high, medium, or low priority based on sender, subject, and urgency cues
- **Draft Writer** — generates concise reply drafts for high-priority emails only

All Gmail access is authenticated through [Scalekit AgentKit](https://docs.scalekit.com/agentkit/overview/). Scalekit handles OAuth token storage, refresh, and tool execution via MCP — your code never touches raw tokens.

Scalekit provides auth and actions on behalf of users, with 500+ connectors and 20,000+ tools.

## Prerequisites

- Python 3.10+
- A [Scalekit account](https://app.scalekit.com)
- A Gmail AgentKit connection configured in the Scalekit Dashboard
- An MCP config that includes Gmail tools (e.g. `gmail-user-tools`)
- An OpenAI API key (or any OpenAI-compatible LLM endpoint)

## Setup

```bash
git clone https://github.com/scalekit-developers/crewai-scalekit-example.git
cd crewai-scalekit-example

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in your credentials (see below)
```

## Configure Scalekit connections

1. Open [app.scalekit.com](https://app.scalekit.com) → **AgentKit** → **Connections** → **Create Connection** for **Gmail**.
2. Note the **Connection name** — the code uses this to resolve the user's connected account.
3. Go to **AgentKit** → **MCP Configs** and create a config (e.g. `gmail-user-tools`) that includes Gmail tools. Set `SCALEKIT_MCP_CONFIG_NAME` in your `.env` to match.
4. Get your API credentials at **Settings** → **API Credentials** and fill them into `.env`.

| Variable | Where to find it |
|---|---|
| `SCALEKIT_ENV_URL` | Dashboard → Settings → Environment URL |
| `SCALEKIT_CLIENT_ID` | Dashboard → API Credentials |
| `SCALEKIT_CLIENT_SECRET` | Dashboard → API Credentials |
| `SCALEKIT_MCP_CONFIG_NAME` | Dashboard → AgentKit → MCP Configs (config name) |
| `SCALEKIT_USER_IDENTIFIER` | Your app's user ID (e.g. email or opaque ID) |
| `OPENAI_API_KEY` | Your LLM provider |

## Run

```bash
python agent.py
```

On first run, the script checks whether the user has an active Gmail connection. If not, it prints an authorization link:

```
[gmail] Authorization required.
Open this link:

  https://auth.scalekit.dev/connect/...

Press Enter after authorizing...
```

Complete the OAuth flow in the browser, then press Enter. On subsequent runs, authorization is skipped automatically.

The crew then runs three tasks in sequence and prints a final summary:

```
============================================================
CREW RESULT
============================================================
## High-Priority Emails — Draft Replies

1. Subject: "Q1 roadmap feedback needed"
   From: Sarah Chen
   Priority: HIGH
   Draft: "Hi Sarah, thanks for flagging this. I'll review ..."
...
```

## How it works

```
┌─────────────────────────────────────────────┐
│  Scalekit Dashboard                         │
│  - Gmail connection (OAuth)                 │
│  - MCP config (gmail-user-tools)            │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│  agent.py                                   │
│                                             │
│  1. Init ScalekitClient                     │
│  2. Ensure Gmail connected (auth if needed) │
│  3. Get MCP URL via ensure_instance()       │
│  4. Connect via MCPServerAdapter            │
│  5. Run CrewAI crew:                        │
│     Scanner → Prioritizer → Drafter         │
└─────────────────────────────────────────────┘
```

The Scalekit MCP server exposes Gmail tools (list messages, read message, send draft, etc.) over the MCP protocol. CrewAI's `MCPServerAdapter` discovers these tools automatically and makes them available to agents.

## Project structure

```
crewai-scalekit-example/
├── agent.py           # Main entrypoint — multi-agent crew
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

## Learn more

- [AgentKit overview](https://docs.scalekit.com/agentkit/overview/)
- [Configure a connection](https://docs.scalekit.com/agentkit/connections/)
- [Generate user MCP URLs](https://docs.scalekit.com/agentkit/mcp/generate-user-urls/)
- [All supported connectors](https://docs.scalekit.com/agentkit/connectors/)
- [CrewAI documentation](https://docs.crewai.com/)
- [agent-auth-examples](https://github.com/scalekit-developers/agent-auth-examples) — more framework examples

## License

MIT