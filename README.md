# claudhaus

> A personal AI command center built on the Claude Agent SDK.  
> The vibe-coded, self-hosted alternative to OpenClaw — built for one person, not a team.

Send a message from your phone. Get your own AI agent on the other end — shaped to your role, connected to your tools, and getting smarter every conversation.

---

## vs OpenClaw

[OpenClaw](https://docs.openclaw.ai) is a multi-provider AI gateway: install it, configure channels and providers via config files, get a dashboard. It's designed to be a general-purpose router between messaging platforms and AI models.

**Claudhaus takes the same idea and rebuilds it from scratch on the Claude Agent SDK:**

| | OpenClaw | Claudhaus |
|---|---|---|
| Model | Multi-provider (Anthropic, OpenAI, Google…) | Claude-native, Claude Agent SDK |
| Setup | Config files + dashboard | One Python file, chat-driven |
| Memory | None built-in | BM25 search over Markdown files, daily notes, long-term MEMORY.md |
| Integrations | Config-file plugins | Self-installing MCP connectors — just ask the bot |
| Skills | Static plugins | Teachable via chat, hot-loaded, no restart |
| Sub-agents | Not built-in | Spawnable via chat with own workspaces and tool sets |
| Self-improvement | No | Main edits its own source code, syntax-checks, restarts |
| Target | Teams, multi-user | One person, personal ops |
| Philosophy | Gateway and router | A person, not a pipeline |

Claudhaus is what you build when you want one Claude agent that knows you, learns your workflows, connects to your tools, and gets smarter every day — not a dashboard you configure.

---

## What this is

A single Claude-powered agent connected to Telegram — shaped entirely by you. Name it, define its role, connect it to your tools, and teach it your workflows just by chatting with it. Memory persists across sessions via plain Markdown files you can read and edit directly.

Everything new — connectors, skills, sub-agents — is added by chatting with your agent. No config files. No restarts for most things. No code changes required.

---

## Prerequisites

- **Claude Code subscription** with an active `claude` CLI login (`claude --version` should work)
- **Python 3.10+**
- **Node.js 18+** (required by the `claude` CLI and MCP servers)
- **git**
- A Telegram account

**Important:** Do not set `ANTHROPIC_API_KEY`. Auth rides on `~/.claude/.credentials.json` (Claude CLI OAuth). Setting the API key switches billing from your subscription to metered API calls.

---

## Quick start

```bash
git clone https://github.com/JjayFabor/claudhaus.git
cd claudhaus
python3 scripts/setup.py
```

The setup wizard will:
1. Check prerequisites
2. Create `.env` from `.env.example`
3. Prompt for your Telegram bot token
4. Create runtime directories and copy soul file templates
5. Create and populate a Python venv
6. Initialize the SQLite database
7. Optionally install and enable systemd user units (Linux/WSL2)

Then:

```bash
source .venv/bin/activate
# Fill in agents/shared/USER_PROFILE.md with your context
# Fill in .env: TELEGRAM_ALLOWED_USER_IDS (get your ID via /whoami after first run)
python agents/main/agent.py
```

Or if you installed the systemd units: `systemctl --user start claude-main.service`

---

## Architecture

```
Telegram/Discord message (text, photo, or voice)
      ↓ photo → saved to workspace/media/; voice → Whisper transcript
agents/main/agent.py        ← async bot runner (Telegram + Discord)
      ↓
Claude Agent SDK            ← spawns claude CLI subprocess per turn
      ↓
Main (claude)               ← soul files + MEMORY.md + daily notes + CLAUDE.md + skills
      ↓
Tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch
     + Memory tools: search, write long-term, write daily
     + Connector tools: list, add, remove (self-installing MCP)
     + Skill tools: list, read, write, delete (hot-loaded, no restart)
     + Sub-agent tools: list, create, run (own workspace + tool set)
     + Scheduler tools: add, list, remove (recurring tasks, SQLite-backed)
     + Any MCP servers configured via `claude mcp add`
```

### Dual instruction set

Every instruction file exists in two forms:

| File | Committed | Purpose |
|------|-----------|---------|
| `agents/main/CLAUDE.md` | Yes | Generic template — works for any user out of the box |
| `agents/main/CLAUDE.personal.md` | No (gitignored) | Your real context, preferences, business specifics |

At startup, if `CLAUDE.personal.md` exists it's used; otherwise `CLAUDE.md`. The same pattern applies to soul files in `agents/shared/`.

---

## Make it yours

Claudhaus ships with a generic agent called "Main." The setup wizard creates your personal version:

```bash
python3 scripts/setup.py
```

It asks for your agent's **name**, **role**, and **tone**, then generates `agents/main/CLAUDE.personal.md` — gitignored, never committed. Examples:

| Name | Role |
|------|------|
| Scout | Sales ops specialist — HubSpot, outreach, pipeline reporting |
| Sage | Research analyst — finds, summarises, synthesises |
| Dev | Senior engineer — writes, reviews, and debugs code |
| Aria | Personal knowledge manager and general operator |

Fill in `agents/shared/USER_PROFILE.md`, `BUSINESS_CONTEXT.md`, and `HOUSE_RULES.md` to give your agent personal context — who you are, what you're building, and how you want it to behave.

See **[docs/customizing-your-agent.md](docs/customizing-your-agent.md)** for the full guide including example personas.

---

## Memory

All memory is plain Markdown on disk — readable and editable in any text editor.

- **`MEMORY.md`** — long-term durable facts, preferences, decisions
- **`memory/YYYY-MM-DD.md`** — daily running context, auto-loaded for today and yesterday
- **`DREAMS.md`** — nightly consolidation candidates (human-reviewed before promotion to MEMORY.md); enable with `DREAMING_ENABLED=true`
- **Search** — BM25 keyword search across all memory files, live-updated via file watcher

---

## Connectors

Add integrations by chatting with Main — no terminal commands needed.

> *"Add the GitHub connector"*

Main walks you through credentials, runs `claude mcp add`, writes the token to `.env`, and restarts itself. Supported out of the box:

GitHub · HubSpot · Slack · Linear · Notion · Google Drive · Gmail · Google Calendar · PostgreSQL · SQLite · Stripe · Jira

Add any other MCP server manually:
```bash
claude mcp add <name> -s user -- <command>
```

See `docs/connectors.md` for full setup instructions.

---

## Skills

Skills are Markdown files injected into the system prompt on every turn — no restart required.

> *"Remember that when I ask for HubSpot contacts, always format them as a table with Name, Title, Company, Email, Phone"*

Main creates a skill file and applies that behaviour from then on. Skills are personal and gitignored.

---

## Sub-agents

Main can create and run specialist agents on demand. Each has its own workspace, system prompt, and restricted tool set.

> *"Create a researcher sub-agent with only WebSearch and WebFetch"*  
> *"Use the researcher to find the top 5 ERP vendors targeting APAC financial services"*

Main delegates the task, the sub-agent runs in its own workspace, and Main formats the result for you. Sub-agent definitions are personal and gitignored.

---

## Self-improvement

Main can read and edit its own source code.

> *"Add a /history command that shows my last 10 messages"*

Main reads the relevant files, makes the change, runs a syntax check (`python -m py_compile`), and restarts itself. For skills and sub-agents, no restart is needed — they load on the next turn.

---

## Images, voice, and files

Send a photo and Main analyzes it — diagrams, screenshots, documents, anything Claude can read visually.

Send a voice message and Main transcribes it via Whisper and responds as if you typed it.

Send any file — code, text, CSV, JSON, PDF — and Main reads it directly into context. Attach a caption to guide what to do with it.

Configure voice transcription in `.env`:
```
WHISPER_PROVIDER=openai   # or: local (faster-whisper, CPU), none (disabled)
OPENAI_API_KEY=sk-...     # required for openai provider
```

For PDF support: `pip install pypdf`

---

## Scheduled tasks

Ask Main to run any task on a recurring schedule. Tasks persist in SQLite and resume on restart.

> *"Every morning at 8am, pull my HubSpot pipeline and send me a summary"*  
> *"Every 30 minutes, check if the staging server is responding"*

Manage via chat: *"list my scheduled tasks"* / *"remove task #3"*

---

## Discord

Set `DISCORD_BOT_TOKEN` in `.env` and Main appears in Discord too — same memory, same tools, same sessions. DM the bot directly, or @-mention it in a server channel.

---

## Telegram commands

| Command | Description |
|---------|-------------|
| `/start` | Confirm the bot is online |
| `/whoami` | Show your Telegram user and chat IDs |
| `/reset` | Clear session and start fresh |
| `/status` | Uptime, session count, memory sizes |
| `/restart` | Restart the bot process |

---

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN_MAIN` | — | Main bot token from BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | — | Comma-separated Telegram user IDs |
| `TELEGRAM_ALLOWED_CHAT_IDS` | — | Group/channel IDs (DMs only if empty) |
| `MAIN_EXTRA_TOOLS` | `*` | `*` = all tools; comma-list to restrict |
| `WHISPER_PROVIDER` | `none` | Voice transcription: `openai`, `local`, or `none` |
| `OPENAI_API_KEY` | — | Required when `WHISPER_PROVIDER=openai` |
| `DISCORD_BOT_TOKEN` | — | Discord bot token (leave blank to disable) |
| `DISCORD_ALLOWED_USER_IDS` | — | Comma-separated Discord user IDs (empty = allow all) |
| `DISCORD_ALLOWED_GUILD_IDS` | — | Comma-separated server IDs (empty = allow all) |
| `DREAMING_ENABLED` | `false` | Nightly memory consolidation sweep |
| `DREAMING_LOOKBACK_DAYS` | `30` | Days of notes to sweep |
| `DREAMING_PROMOTION_THRESHOLD` | `0.6` | Score threshold for DREAMS.md candidates |
| `DASHBOARD_PORT` | `8000` | Dashboard listen port (not yet built) |
| `OBSIDIAN_VAULT_PATH` | — | Absolute path to Obsidian vault (not yet built) |

---

## Platform notes

### WSL2

Requires `systemd=true` in `/etc/wsl.conf` and `vmIdleTimeout=-1` in `~/.wslconfig` to prevent idle shutdown. See `docs/wsl-keepalive.md`.

### Linux — auto-start

```bash
bash scripts/install-systemd.sh
```

Copies all unit files, enables linger (survives logout), starts `claude-main.service`, and enables nightly backup and dreaming timers.

### macOS

```bash
cp systemd/com.claudecommandcenter.main.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.claudecommandcenter.main.plist
```

### Docker

```bash
docker compose up -d
```

**Critical:** the `~/.claude` volume mount is required for CLI auth. See `docker-compose.yml`.

---

## FAQ

**Q: Why not set `ANTHROPIC_API_KEY`?**
Setting it switches billing from your Claude Code subscription to metered API calls. Auth via `~/.claude/.credentials.json` is free under your subscription.

**Q: How do I find my Telegram user ID?**
Start the bot and send `/whoami`. It replies with your numeric user ID. Put that in `TELEGRAM_ALLOWED_USER_IDS`.

**Q: How do I reset a conversation?**
Send `/reset`. The next message starts a fresh Claude session.

**Q: What happens when the context window fills up?**
The memory flush system writes important facts to `MEMORY.md` before compaction. Nothing is lost.

**Q: Is this safe to use on shared machines?**
`bypassPermissions` mode gives Main full tool access. Only run this on machines you control, with the Telegram allowlist configured.

**Q: Can multiple people use one instance?**
Add their user IDs to `TELEGRAM_ALLOWED_USER_IDS`. Each Telegram chat gets its own Claude session. Memory is currently shared across all users — good for a household, not for a team.

---

## Legal & compliance

**Claudhaus is an independent open-source project. It is not affiliated with, endorsed by, or supported by Anthropic.**

### You must comply with Anthropic's terms

Using Claudhaus requires a valid Claude Code subscription or Anthropic API key. By using this software you agree to:

- [Anthropic Terms of Service](https://www.anthropic.com/legal/consumer-terms)
- [Anthropic Usage Policy](https://www.anthropic.com/legal/usage-policy)
- [Claude Agent SDK terms](https://www.anthropic.com/legal/consumer-terms) (same as above — the SDK is part of Claude Code)

You are solely responsible for obtaining and maintaining valid credentials, and for ensuring your use of Claude through this software complies with Anthropic's policies.

### `bypassPermissions` mode

Claudhaus runs the Claude agent with `permission_mode="bypassPermissions"`, which means the agent can execute shell commands, read and write files, and call external APIs without per-action prompts. **Only run Claudhaus on machines you control and trust.** You are responsible for the actions taken by your agent.

### No API keys included

Claudhaus does not include, distribute, or proxy any API keys. You provide your own credentials via `.env`. Keep your `.env` file private — it is gitignored by default.

### Responsible use

Claudhaus gives your agent access to powerful tools including Bash execution, file system access, and external service integrations. Use it responsibly and in accordance with the terms of any third-party services you connect (GitHub, HubSpot, Slack, etc.).

---

## License

MIT — see [LICENSE](LICENSE).
