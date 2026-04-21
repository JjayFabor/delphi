#!/usr/bin/env python3
"""
First-run setup wizard for claude-command-center.
Idempotent — safe to re-run at any time.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def banner(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def check(label: str, ok: bool, fix: str = "") -> None:
    status = "✓" if ok else "✗"
    print(f"  {status}  {label}")
    if not ok:
        if fix:
            print(f"     → {fix}")
        sys.exit(1)


def require_command(name: str, install_hint: str) -> None:
    check(f"{name} in PATH", shutil.which(name) is not None, install_hint)


def main() -> None:
    banner("claude-command-center setup")

    # ── Prerequisites ──────────────────────────────────────────────────────────
    banner("Checking prerequisites")
    require_command("python3", "Install Python 3.10+ from https://python.org")
    require_command("node", "Install Node.js 18+ from https://nodejs.org")
    require_command("git", "Install git from https://git-scm.com")
    require_command("claude", "Install Claude Code CLI: https://claude.ai/code")

    py_version = sys.version_info
    check(
        f"Python >= 3.10 (found {py_version.major}.{py_version.minor})",
        py_version >= (3, 10),
        "Upgrade Python to 3.10 or newer",
    )

    # ── .env ──────────────────────────────────────────────────────────────────
    banner("Environment file")
    if not ENV_FILE.exists():
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print("  Created .env from .env.example")
    else:
        print("  .env already exists — skipping")

    # Prompt for bot token if missing
    env_content = ENV_FILE.read_text()
    if "TELEGRAM_BOT_TOKEN_MAIN=" in env_content and "TELEGRAM_BOT_TOKEN_MAIN=\n" in env_content:
        print("\n  To create a Telegram bot:")
        print("    1. Open Telegram and search for @BotFather")
        print("    2. Send /newbot and follow the prompts")
        print("    3. Copy the token BotFather gives you")
        token = input("\n  Paste your Main bot token (or press Enter to skip): ").strip()
        if token:
            updated = env_content.replace("TELEGRAM_BOT_TOKEN_MAIN=", f"TELEGRAM_BOT_TOKEN_MAIN={token}")
            ENV_FILE.write_text(updated)
            print("  Token saved to .env")

    # ── Directories ───────────────────────────────────────────────────────────
    banner("Creating directories")
    for d in ["data", "logs", "workspaces/main", "workspaces/main/memory", "workspaces/main/sessions"]:
        path = ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓  {d}/")

    # ── Soul files ────────────────────────────────────────────────────────────
    banner("Soul files (agents/shared/)")
    shared = ROOT / "agents" / "shared"
    for example in shared.glob("*.example.md"):
        target = shared / example.name.replace(".example.md", ".md")
        if not target.exists():
            shutil.copy(example, target)
            print(f"  Created {target.name} from template")
        else:
            print(f"  {target.name} already exists — skipping")

    # ── Agent customization ───────────────────────────────────────────────────
    banner("Customize your agent")
    generic = ROOT / "agents" / "main" / "CLAUDE.md"
    personal = ROOT / "agents" / "main" / "CLAUDE.personal.md"

    if personal.exists():
        print("  CLAUDE.personal.md already exists — skipping")
    else:
        print("  Let's set up your personal agent. Press Enter to keep the default.")
        print()

        agent_name = input("  Agent name [Main]: ").strip() or "Main"

        print()
        print("  Role examples:")
        print("    • senior software engineer and personal AI operator  (default)")
        print("    • sales operations specialist focused on CRM and outreach")
        print("    • research analyst — finds, summarises, and synthesises information")
        print("    • coding assistant — write, review, debug, and ship code")
        print()
        agent_role = (
            input("  Agent role (one sentence) [senior software engineer and personal AI operator]: ").strip()
            or "senior software engineer and personal AI operator"
        )

        print()
        print("  Tone examples:")
        print("    • Match the register of the user's message  (default)")
        print("    • Always formal and professional")
        print("    • Warm, encouraging, and supportive")
        print()
        agent_tone = (
            input("  Tone [Match the register of the user's message]: ").strip()
            or "Match the register of the user's message"
        )

        template = generic.read_text(encoding="utf-8")

        # Strip the HTML comment customization guide block before writing personal file
        import re as _re
        template = _re.sub(r"<!--\n╔.*?╚.*?╝\n-->\n\n", "", template, flags=_re.DOTALL)

        # Substitute placeholders
        customized = template.replace("[Your Agent Name]", agent_name)
        customized = customized.replace(
            "a personal AI operator and senior software engineer",
            f"a {agent_role}",
        )
        customized = customized.replace(
            "Match the register of the user's message — technical when they're technical,\ncasual when they're casual.",
            agent_tone,
        )
        # Update self-improvement path hint if they use a different directory
        personal.write_text(customized, encoding="utf-8")
        print(f"\n  ✓  Created CLAUDE.personal.md for agent '{agent_name}'")
        print(f"  Edit it any time: {personal}")
        print()

        open_it = input("  Open it in your editor now? (y/n): ").strip().lower()
        if open_it == "y":
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(personal)])

    # ── Virtual environment ───────────────────────────────────────────────────
    banner("Python virtual environment")
    if not VENV.exists():
        print("  Creating .venv...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    else:
        print("  .venv already exists — skipping creation")

    pip = VENV / "bin" / "pip"
    print("  Installing requirements.txt...")
    subprocess.run([str(pip), "install", "--quiet", "-r", str(ROOT / "requirements.txt")], check=True)
    print("  ✓  Dependencies installed")

    # ── SQLite schema ─────────────────────────────────────────────────────────
    banner("Database")
    db_path = ROOT / "data" / "memory.db"
    if not db_path.exists():
        try:
            import sqlite3
            con = sqlite3.connect(db_path)
            con.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    chat_id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)
            con.close()
            print("  ✓  data/memory.db initialized")
        except Exception as e:
            print(f"  ✗  Failed to create database: {e}")
    else:
        print("  data/memory.db already exists — skipping")

    # ── Systemd ───────────────────────────────────────────────────────────────
    banner("Systemd auto-start (Linux only)")
    if shutil.which("systemctl"):
        answer = input("  Install and enable systemd user units? (y/n): ").strip().lower()
        if answer == "y":
            install_script = ROOT / "scripts" / "install-systemd.sh"
            install_script.chmod(0o755)
            result = subprocess.run([str(install_script)], capture_output=False)
            if result.returncode != 0:
                print("  ✗  systemd install failed — run scripts/install-systemd.sh manually")
        else:
            print("  Skipped — run scripts/install-systemd.sh manually when ready")
    else:
        print("  systemctl not found — skipping (not Linux or systemd unavailable)")

    # ── Done ──────────────────────────────────────────────────────────────────
    banner("Setup complete")
    print("  Next steps:")
    print("    1. Fill in TELEGRAM_ALLOWED_USER_IDS in .env (run /whoami in Telegram)")
    print("    2. Edit agents/shared/USER_PROFILE.md with your personal context")
    print("    3. Edit agents/shared/BUSINESS_CONTEXT.md and HOUSE_RULES.md")
    print("    4. Activate the venv: source .venv/bin/activate")
    print("    5. Start the bot: python agents/main/agent.py")
    print("       (or let systemd manage it if you installed the units above)")
    print()


if __name__ == "__main__":
    main()
