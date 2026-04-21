# Changelog

All notable changes to this project are documented here.

## [Unreleased]

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
