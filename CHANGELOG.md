# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.7.0] — Skills & Sub-agents — 2026-04-21

### Added
- `agents/main/skills.py` — skill loader; skills are markdown files in `agents/main/skills/`
- Four skill SDK tools: `skill_list`, `skill_read`, `skill_write`, `skill_delete`
- Skills injected into system prompt on every turn via `build_system_prompt()` — no restart required
- `agents/main/subagents.py` — sub-agent registry and async runner
- Three sub-agent SDK tools: `subagent_list`, `subagent_create`, `subagent_run`
- Sub-agents get own workspace (`workspaces/<name>/`), system prompt (`agents/<name>/CLAUDE.md`), and tool config (`agents/<name>/config.json`)
- `CLAUDE.md` — added skills and sub-agent workflow instructions

## [0.6.1] — Connectors — 2026-04-21

### Added
- `agents/main/connectors.py` — registry of 12 connectors (GitHub, HubSpot, Slack, Linear, Notion, Google Drive/Gmail/Calendar, Postgres, SQLite, Stripe, Jira) with install/remove functions
- Four in-process SDK tools: `connector_list`, `connector_add`, `connector_remove`, `connector_info`
- `/restart` Telegram command — sends confirmation then restarts via systemd or os.execv
- Auto-restart after successful `connector_add` or `connector_remove` — bot restarts once reply is delivered
- `MAIN_EXTRA_TOOLS` env var — set to `*` (default) to allow all MCP tools; comma-separate specific names to restrict
- `docs/connectors.md` — manual setup reference
- `.env.example` connectors section — credential placeholders

### Changed
- `run_claude()` uses `_build_allowed_tools()` — dynamic tool list instead of hardcoded array
- `CLAUDE.md` — added connector workflow instructions (collect credentials → connector_add → auto-restart)

## [0.6.0] — Phase 6 — 2026-04-21

### Added
- `systemd/claude-backup.service` + `claude-backup.timer` — daily backup at 02:00, runs `scripts/backup.sh`
- `scripts/install-systemd.sh` — idempotent installer: copies all units, enables linger, enables + starts services
- Startup/restart notification — bot sends "Main is online." to all allowed user IDs on every start via `post_init` hook
- `/status` command — shows uptime, active session count, MEMORY.md size, today's daily note size
- `scripts/setup.py` — added systemd install step (interactive, calls `install-systemd.sh`)

## [0.4.0] — Phase 4 — 2026-04-21

### Added
- `memory/index.py` — BM25 index over MEMORY.md + daily notes, file watcher (5s poll), chunker with overlap
- `memory/search.py` — BM25 search with token-presence filter (works correctly on small corpora)
- `memory/flush.py` — pre-compaction flush manager; fires silent turn before context window fills
- `memory/dreaming.py` — nightly consolidation sweep (disabled by default, writes DREAMS.md candidates)
- Four in-process SDK tools: `memory_search`, `memory_write_long_term`, `memory_write_daily`, `memory_read_file`
- Updated session start injection: soul files → MEMORY.md → today/yesterday notes → CLAUDE.md
- `~/memory`, `~/MEMORY.md`, `~/DREAMS.md` symlinks so bundled claude CLI writes to correct workspace paths
- Today's daily note seeded on startup if it doesn't exist

## [0.2.0] — Phase 2 — 2026-04-21

### Added
- `permission_mode="bypassPermissions"` — full tool execution, no SDK-level prompts
- `setting_sources=["user"]` — Main inherits MCP servers from ~/.claude.json

## [0.1.0] — Phase 1 — 2026-04-21

### Added
- `agents/main/agent.py` — full Telegram bot runner with Claude Agent SDK integration
- `load_instructions()` utility — personal override takes precedence over generic CLAUDE.md
- `build_system_prompt()` — concatenates soul files + instruction file at session start
- SQLite schema init in `init_db()` — `conversations` and `sessions` tables
- Session persistence — each chat_id gets its own Claude session; resumes across messages
- Allowlist enforcement — silent drop for unauthorized user IDs and chat IDs
- `/start`, `/whoami`, `/reset` Telegram commands
- Typing indicator that refreshes every 4 seconds during long Claude runs
- Message chunking — replies over 4000 chars split at paragraph/line/word boundaries
- Rotating log handler — `logs/main.log`, 5 MB max, 3 backups
- `.venv` with `claude-agent-sdk`, `python-telegram-bot`, `python-dotenv`, `aiosqlite`

## [0.0.1] — Phase 0 — 2026-04-21

### Added
- Full project directory structure
- `.gitignore` covering credentials, workspaces, personal overrides
- `.env.example` with all configuration variables documented
- `requirements.txt` with core and phase-gated dependencies
- `agents/main/CLAUDE.md` — generic committed instruction template
- `agents/shared/*.example.md` — soul file templates (USER_PROFILE, BUSINESS_CONTEXT, HOUSE_RULES)
- `agents/main/agent.py` — stub with `load_instructions()` utility
- `scripts/setup.py` — idempotent first-run wizard
- `scripts/backup.sh` — daily backup with 14-day retention
- `scripts/update.sh` — pip upgrade with session-safe restart
- systemd user units: `claude-main.service`, `claude-dashboard.service`, `claude-memory-dreaming.service/.timer`
- macOS launchd plist: `com.claudecommandcenter.main.plist`
- `Dockerfile` and `docker-compose.yml` with `~/.claude` volume mount
- `docs/wsl-keepalive.md` — WSL2 systemd + idle timeout setup
- `docs/cloudflare-tunnel.md` — phone access to dashboard
- GitHub issue templates and PR template
- `LICENSE` (MIT)
- `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- `BUILD_PLAN.md` — complete build plan for all phases
- Stub modules: `memory/`, `dashboard/`, `obsidian/`
