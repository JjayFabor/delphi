"""
agents/main/agent.py — Main bot runner.

One Telegram bot, one Claude agent, full session persistence + memory.
"""

import asyncio
import contextvars
import html
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import date, time as dtime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_start_time = time.time()
_restart_requested = False
_mcp_ready_event: Optional[asyncio.Event] = None
_MCP_PROBE_TIMEOUT = 60  # seconds to wait for MCP init before giving up
_current_chat_id: contextvars.ContextVar[int] = contextvars.ContextVar("current_chat_id", default=0)
_app: Optional["Application"] = None  # set after Application.build(); used by scheduler tools
_active_tasks: dict[int, asyncio.Task] = {}  # chat_id → running handler task

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import claude_agent_sdk as sdk

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_DIR = Path(__file__).resolve().parent
SHARED_DIR = ROOT / "agents" / "shared"
WORKSPACE = ROOT / "workspaces" / "main"
DB_PATH = ROOT / "data" / "memory.db"
LOG_PATH = ROOT / "logs" / "main.log"

sys.path.insert(0, str(ROOT))

from agents.main.connectors import (
    list_connectors,
    get_connector_info,
    get_installed_connectors,
    add_connector,
    remove_connector,
    REGISTRY as CONNECTOR_REGISTRY,
)
from agents.main import skills as _skills_mod
from agents.main import media as _media_mod
from agents.main import discord_bot as _discord_mod
from agents.main import self_edit as _self_edit_mod
from agents.main.subagents import list_subagents, create_subagent, run_subagent
from agents.main.scheduler import (
    init_scheduler_table,
    db_add_task, db_remove_task, db_list_tasks, db_all_enabled_tasks,
    parse_schedule, parse_once,
)
from agents.main.shared_context import (
    init_shared_context_tables,
    db_upsert_user,
    db_resolve_user,
    db_share_context,
    db_get_unacknowledged_shared,
    db_mark_acknowledged,
    db_revoke_shared,
    db_list_shared,
    format_shared_note,
)

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
os.umask(0o077)  # new files (logs, DB journals) created owner-only (600/700)
_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[_handler, logging.StreamHandler()],
)
logger = logging.getLogger("main")

load_dotenv(ROOT / ".env")

# ── Config ─────────────────────────────────────────────────────────────────────
_bot_token = os.getenv("TELEGRAM_BOT_TOKEN_MAIN")
if not _bot_token:
    raise SystemExit(
        "ERROR: TELEGRAM_BOT_TOKEN_MAIN is not set in .env. "
        "Create a bot via @BotFather and add the token to your .env file."
    )
BOT_TOKEN: str = _bot_token

_raw_user_ids = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {
    int(x.strip()) for x in _raw_user_ids.split(",") if x.strip()
}
if not ALLOWED_USER_IDS:
    logger.warning(
        "TELEGRAM_ALLOWED_USER_IDS is empty — all incoming messages will be rejected. "
        "Add your Telegram user ID to .env to allow access."
    )

_raw_chat_ids = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: set[int] = {
    int(x.strip()) for x in _raw_chat_ids.split(",") if x.strip()
}

TG_MAX_CHARS = 4000

# Max seconds to wait for a Claude response before killing the subprocess.
# Prevents the bot from freezing indefinitely on a stuck Claude process.
# Override with CLAUDE_TIMEOUT_SECONDS in .env (default: 5 minutes).
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "300"))

# ── Tool allowlist ─────────────────────────────────────────────────────────────
# MAIN_EXTRA_TOOLS in .env: comma-separated tool names to add on top of base set.
# Set to "*" to allow every tool (all MCP connectors, no restriction).
_BASE_TOOLS = [
    "Bash", "Read", "Write", "Edit", "Glob", "Grep",
    "WebSearch", "WebFetch", "TodoWrite",
    "memory_search", "memory_write_long_term", "memory_write_daily", "memory_read_file",
    "wiki_write", "wiki_read", "wiki_list",
    "connector_list", "connector_add", "connector_remove", "connector_info",
    "skill_list", "skill_read", "skill_write", "skill_delete",
    "subagent_list", "subagent_create", "subagent_run",
    "scheduler_add", "scheduler_list", "scheduler_remove", "schedule_once",
    "send_message",
    "self_edit",
    "learn",
    "run_bg", "job_wait", "job_status",
]

def _build_allowed_tools() -> Optional[list[str]]:
    extra_env = os.getenv("MAIN_EXTRA_TOOLS", "").strip()
    if extra_env == "*":
        return None  # unrestricted — all MCP tools available
    extras = [t.strip() for t in extra_env.split(",") if t.strip()]
    return _BASE_TOOLS + extras


# ── Memory index (initialised in main()) ──────────────────────────────────────
from memory.index import MemoryIndex
from memory.search import search as _mem_search
from memory.flush import FlushManager

_mem_index: Optional[MemoryIndex] = None
_flush_mgr = FlushManager()


# ── In-process memory tools ───────────────────────────────────────────────────

@sdk.tool(
    name="memory_search",
    description="Search long-term memory and daily notes for past facts, preferences, and decisions. Call this before answering questions about past work or preferences.",
    input_schema={"query": str, "limit": int},
)
async def tool_memory_search(args: dict) -> dict:
    query = args.get("query", "")
    limit = int(args.get("limit", 5))
    if _mem_index is None:
        return {"content": [{"type": "text", "text": "Memory index not initialised."}]}
    result = _mem_search(_mem_index, query, limit=limit)
    return {"content": [{"type": "text", "text": result}]}


@sdk.tool(
    name="memory_write_long_term",
    description="Append a durable fact, preference, or decision to MEMORY.md. Use for things that should be remembered across all future sessions.",
    input_schema={"content": str},
)
async def tool_memory_write_long_term(args: dict) -> dict:
    content = args.get("content", "").strip()
    if not content:
        return {"content": [{"type": "text", "text": "Error: content is empty."}], "is_error": True}
    memory_md = WORKSPACE / "MEMORY.md"
    memory_md.parent.mkdir(parents=True, exist_ok=True)
    with memory_md.open("a", encoding="utf-8") as f:
        f.write(f"\n{content}\n")
    if _mem_index:
        _mem_index.reindex_file(memory_md)
    logger.info("memory_write_long_term: wrote %d chars", len(content))
    return {"content": [{"type": "text", "text": f"Written to MEMORY.md: {content[:80]}..."}]}


@sdk.tool(
    name="memory_write_daily",
    description="Append an observation or context note to today's daily memory file (memory/YYYY-MM-DD.md). Use for short-term context that may be useful for the next few days.",
    input_schema={"content": str},
)
async def tool_memory_write_daily(args: dict) -> dict:
    content = args.get("content", "").strip()
    if not content:
        return {"content": [{"type": "text", "text": "Error: content is empty."}], "is_error": True}
    today = date.today().isoformat()
    daily_file = WORKSPACE / "memory" / f"{today}.md"
    daily_file.parent.mkdir(parents=True, exist_ok=True)
    if not daily_file.exists():
        daily_file.write_text(f"# {today}\n\n", encoding="utf-8")
    with daily_file.open("a", encoding="utf-8") as f:
        f.write(f"- {content}\n")
    if _mem_index:
        _mem_index.reindex_file(daily_file)
    logger.info("memory_write_daily: wrote to %s", daily_file.name)
    return {"content": [{"type": "text", "text": f"Written to {daily_file.name}: {content[:80]}"}]}


@sdk.tool(
    name="memory_read_file",
    description="Read a memory file by name. Valid values: 'MEMORY.md', 'DREAMS.md', or a date like '2026-04-21' to read that day's notes.",
    input_schema={"path": str},
)
async def tool_memory_read_file(args: dict) -> dict:
    path_arg = args.get("path", "").strip()
    if not path_arg:
        return {"content": [{"type": "text", "text": "Error: path is required."}], "is_error": True}

    if path_arg in ("MEMORY.md", "DREAMS.md"):
        target = WORKSPACE / path_arg
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", path_arg):
        target = WORKSPACE / "memory" / f"{path_arg}.md"
    else:
        return {"content": [{"type": "text", "text": f"Invalid path: {path_arg!r}. Use 'MEMORY.md', 'DREAMS.md', or a YYYY-MM-DD date."}], "is_error": True}

    if not target.exists():
        return {"content": [{"type": "text", "text": f"{path_arg} does not exist yet."}]}
    text = target.read_text(encoding="utf-8")
    return {"content": [{"type": "text", "text": text or "(empty)"}]}


# ── Wiki tools ────────────────────────────────────────────────────────────────

@sdk.tool(
    name="wiki_write",
    description=(
        "Create or overwrite a wiki page. Use path as a slash-separated topic slug "
        "like 'database/schema' or 'hubspot/properties'. Content should be clean markdown. "
        "Call this to file knowledge discovered during a conversation so it persists for future sessions."
    ),
    input_schema={"path": str, "content": str},
)
async def tool_wiki_write(args: dict) -> dict:
    path_arg = args.get("path", "").strip().strip("/")
    content = args.get("content", "").strip()
    if not path_arg:
        return {"content": [{"type": "text", "text": "Error: path is required."}], "is_error": True}
    if not content:
        return {"content": [{"type": "text", "text": "Error: content is empty."}], "is_error": True}
    target = WORKSPACE / "wiki" / (path_arg if path_arg.endswith(".md") else f"{path_arg}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    if _mem_index:
        _mem_index.reindex_file(target)
    logger.info("wiki_write: wrote %s (%d chars)", target.relative_to(WORKSPACE), len(content))
    return {"content": [{"type": "text", "text": f"Wiki page written: wiki/{path_arg}.md"}]}


@sdk.tool(
    name="wiki_read",
    description="Read a wiki page in full by its path slug (e.g. 'database/schema' or 'hubspot/properties').",
    input_schema={"path": str},
)
async def tool_wiki_read(args: dict) -> dict:
    path_arg = args.get("path", "").strip().strip("/")
    if not path_arg:
        return {"content": [{"type": "text", "text": "Error: path is required."}], "is_error": True}
    target = WORKSPACE / "wiki" / (path_arg if path_arg.endswith(".md") else f"{path_arg}.md")
    if not target.exists():
        return {"content": [{"type": "text", "text": f"Wiki page not found: wiki/{path_arg}.md"}]}
    text = target.read_text(encoding="utf-8")
    return {"content": [{"type": "text", "text": text or "(empty)"}]}


@sdk.tool(
    name="wiki_list",
    description="List all wiki pages. Returns a tree of topic paths.",
    input_schema={},
)
async def tool_wiki_list(_args: dict) -> dict:
    wiki_dir = WORKSPACE / "wiki"
    if not wiki_dir.exists() or not any(wiki_dir.rglob("*.md")):
        return {"content": [{"type": "text", "text": "Wiki is empty. Use wiki_write to add pages."}]}
    pages = sorted(
        str(p.relative_to(wiki_dir).with_suffix(""))
        for p in wiki_dir.rglob("*.md")
    )
    return {"content": [{"type": "text", "text": "\n".join(pages)}]}


# ── Connector tools ───────────────────────────────────────────────────────────

@sdk.tool(
    name="connector_list",
    description=(
        "List all available connectors (MCP integrations) and whether each is installed. "
        "Call this when the user asks what services Main can connect to, or to show connector status."
    ),
    input_schema={},
)
async def tool_connector_list(_args: dict) -> dict:
    result = list_connectors()
    return {"content": [{"type": "text", "text": result}]}


@sdk.tool(
    name="connector_add",
    description=(
        "Add an integration connector (GitHub, HubSpot, Slack, etc.) by registering the MCP server "
        "and saving credentials to .env. Call this once you have collected all required credentials "
        "from the user. Main will restart automatically after a successful add."
    ),
    input_schema={"name": str, "credentials": dict},
)
async def tool_connector_add(args: dict) -> dict:
    global _restart_requested
    name = args.get("name", "").strip()
    credentials = args.get("credentials", {})
    ok, msg = add_connector(name, credentials)
    if ok:
        _restart_requested = True
    return {"content": [{"type": "text", "text": msg}], **({"is_error": True} if not ok else {})}


@sdk.tool(
    name="connector_remove",
    description="Remove a previously added connector by name. Main will restart to apply the change.",
    input_schema={"name": str},
)
async def tool_connector_remove(args: dict) -> dict:
    global _restart_requested
    name = args.get("name", "").strip()
    ok, msg = remove_connector(name)
    if ok:
        _restart_requested = True
    return {"content": [{"type": "text", "text": msg}], **({"is_error": True} if not ok else {})}


@sdk.tool(
    name="connector_info",
    description=(
        "Get setup instructions and required credentials for a specific connector. "
        "Call this to find out what the user needs to provide before calling connector_add."
    ),
    input_schema={"name": str},
)
async def tool_connector_info(args: dict) -> dict:
    name = args.get("name", "").strip().lower()
    info = get_connector_info(name)
    if not info:
        known = ", ".join(CONNECTOR_REGISTRY.keys())
        return {
            "content": [{"type": "text", "text": f"Unknown connector '{name}'. Available: {known}"}],
            "is_error": True,
        }
    lines = [f"Connector: {name}", f"Description: {info['description']}", ""]
    if info["env_vars"]:
        lines.append("Required credentials:")
        for key, instructions in info["env_vars"].items():
            lines.append(f"\n{key}:\n  {instructions}")
    else:
        lines.append("No credentials required — OAuth flow runs on first use.")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


# ── Skill tools ───────────────────────────────────────────────────────────────

@sdk.tool(
    name="skill_list",
    description="List all saved skills by name with a short preview of their content.",
    input_schema={},
)
async def tool_skill_list(_args: dict) -> dict:
    skills = _skills_mod.list_skills()
    if not skills:
        text = "No skills saved yet."
    else:
        text = "\n".join(f"• {s['name']}: {s['preview']}" for s in skills)
    return {"content": [{"type": "text", "text": text}]}


@sdk.tool(
    name="skill_read",
    description="Read the full content of a saved skill by name.",
    input_schema={"name": str},
)
async def tool_skill_read(args: dict) -> dict:
    content = _skills_mod.read_skill(args.get("name", ""))
    if content is None:
        return {"content": [{"type": "text", "text": "Skill not found."}], "is_error": True}
    return {"content": [{"type": "text", "text": content}]}


@sdk.tool(
    name="skill_write",
    description=(
        "Create or update a skill. Skills are injected into the system prompt on every turn — "
        "no restart needed. Use skills to encode domain knowledge, workflows, formatting rules, "
        "or repeatable procedures. name should be a short slug (e.g. 'hubspot-targets')."
    ),
    input_schema={"name": str, "content": str},
)
async def tool_skill_write(args: dict) -> dict:
    name = args.get("name", "").strip()
    content = args.get("content", "").strip()
    if not name or not content:
        return {"content": [{"type": "text", "text": "name and content are required."}], "is_error": True}
    filename = _skills_mod.write_skill(name, content)
    return {"content": [{"type": "text", "text": f"Skill saved: {filename}"}]}


@sdk.tool(
    name="skill_delete",
    description="Delete a saved skill by name.",
    input_schema={"name": str},
)
async def tool_skill_delete(args: dict) -> dict:
    deleted = _skills_mod.delete_skill(args.get("name", ""))
    msg = f"Skill deleted." if deleted else "Skill not found."
    return {"content": [{"type": "text", "text": msg}], **({"is_error": True} if not deleted else {})}


# ── Sub-agent tools ────────────────────────────────────────────────────────────

@sdk.tool(
    name="subagent_list",
    description="List all available sub-agents with their descriptions and tool configs.",
    input_schema={},
)
async def tool_subagent_list(_args: dict) -> dict:
    agents = list_subagents()
    if not agents:
        text = "No sub-agents defined yet."
    else:
        lines = []
        for a in agents:
            tools_str = ", ".join(a["tools"]) if a["tools"] else "all tools"
            lines.append(f"• {a['name']}: {a['description']} ({tools_str})")
        text = "\n".join(lines)
    return {"content": [{"type": "text", "text": text}]}


@sdk.tool(
    name="subagent_create",
    description=(
        "Create a new sub-agent with its own workspace, system prompt, and tool set. "
        "Sub-agents are specialists — give each a focused role and minimal tool set. "
        "tools should be a list of tool names, or null to allow all tools."
    ),
    input_schema={"name": str, "description": str, "system_prompt": str, "tools": list},
)
async def tool_subagent_create(args: dict) -> dict:
    name = args.get("name", "").strip()
    description = args.get("description", "").strip()
    system_prompt = args.get("system_prompt", "").strip()
    tools = args.get("tools") or None  # empty list → None (all tools)
    if not name or not system_prompt:
        return {"content": [{"type": "text", "text": "name and system_prompt are required."}], "is_error": True}
    path = create_subagent(name, description, system_prompt, tools)
    return {"content": [{"type": "text", "text": f"Sub-agent '{name}' created at {path}"}]}


@sdk.tool(
    name="subagent_run",
    description=(
        "Run a named sub-agent with a specific task. The sub-agent executes in its own workspace "
        "with its own system prompt and returns its result. Use this to delegate focused work: "
        "research, data transformation, drafting, analysis."
    ),
    input_schema={"name": str, "task": str},
)
async def tool_subagent_run(args: dict) -> dict:
    name = args.get("name", "").strip()
    task = args.get("task", "").strip()
    if not name or not task:
        return {"content": [{"type": "text", "text": "name and task are required."}], "is_error": True}
    try:
        result = await run_subagent(name, task)
        return {"content": [{"type": "text", "text": result}]}
    except ValueError as e:
        return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Sub-agent error: {e}"}], "is_error": True}


# ── Scheduler tools ───────────────────────────────────────────────────────────

@sdk.tool(
    name="scheduler_add",
    description=(
        "Schedule a recurring task. The bot will automatically run the task_prompt "
        "at the specified interval and send the result to the user. "
        "schedule_str examples: 'every 30 minutes', 'every 2 hours', "
        "'every day at 9am', 'daily at 14:30'."
    ),
    input_schema={"task_prompt": str, "schedule_str": str},
)
async def tool_scheduler_add(args: dict) -> dict:
    task_prompt = args.get("task_prompt", "").strip()
    schedule_str = args.get("schedule_str", "").strip()
    if not task_prompt or not schedule_str:
        return {"content": [{"type": "text", "text": "task_prompt and schedule_str are required."}], "is_error": True}

    chat_id = _current_chat_id.get()
    if not chat_id:
        return {"content": [{"type": "text", "text": "Cannot determine chat context."}], "is_error": True}

    try:
        task_id = db_add_task(DB_PATH, chat_id, task_prompt, schedule_str)
    except ValueError as e:
        return {"content": [{"type": "text", "text": str(e)}], "is_error": True}

    # Register with the running JobQueue immediately
    if _app and _app.job_queue:
        _register_one_task(_app, {
            "id": task_id, "chat_id": chat_id,
            "task_prompt": task_prompt,
            **_task_schedule_fields(schedule_str),
        })

    return {"content": [{"type": "text", "text": f"Scheduled task #{task_id} created: {schedule_str}"}]}


@sdk.tool(
    name="scheduler_list",
    description="List all scheduled tasks for the current chat.",
    input_schema={},
)
async def tool_scheduler_list(_args: dict) -> dict:
    chat_id = _current_chat_id.get()
    if not chat_id:
        return {"content": [{"type": "text", "text": "Cannot determine chat context."}], "is_error": True}
    tasks = db_list_tasks(DB_PATH, chat_id)
    if not tasks:
        return {"content": [{"type": "text", "text": "No scheduled tasks."}]}
    lines = [f"#{t['id']} [{'+' if t['enabled'] else '-'}] {t['schedule_str']}: {t['task_prompt']}" for t in tasks]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@sdk.tool(
    name="scheduler_remove",
    description="Remove a scheduled task by its ID (shown in scheduler_list).",
    input_schema={"task_id": int},
)
async def tool_scheduler_remove(args: dict) -> dict:
    task_id = int(args.get("task_id", 0))
    chat_id = _current_chat_id.get()
    if not task_id or not chat_id:
        return {"content": [{"type": "text", "text": "task_id is required."}], "is_error": True}

    deleted = db_remove_task(DB_PATH, task_id, chat_id)
    if not deleted:
        return {"content": [{"type": "text", "text": f"Task #{task_id} not found."}], "is_error": True}

    # Remove from running JobQueue
    if _app and _app.job_queue:
        for job in _app.job_queue.get_jobs_by_name(f"task_{task_id}"):
            job.schedule_removal()

    return {"content": [{"type": "text", "text": f"Task #{task_id} removed."}]}


# ── Self-editing tool ─────────────────────────────────────────────────────────

@sdk.tool(
    name="self_edit",
    description=(
        "Safely edit any file in the claudhaus project — your own source code, "
        "CLAUDE.md, skills, sub-agent configs, or any project file. "
        "Creates a backup before editing, syntax-checks Python files, "
        "auto-reverts on any failure, and commits the change to git on success. "
        "Use this instead of raw Edit/Write for all project file changes. "
        "Modes: (a) targeted — provide old_string + new_string; "
        "(b) full rewrite — provide new_content. "
        "Set restart=true to restart the bot after a successful Python edit."
    ),
    input_schema={
        "file_path": str,
        "old_string": str,
        "new_string": str,
        "new_content": str,
        "description": str,
        "replace_all": bool,
        "restart": bool,
    },
)
async def tool_self_edit(args: dict) -> dict:
    global _restart_requested
    file_path = args.get("file_path", "").strip()
    if not file_path:
        return {"content": [{"type": "text", "text": "file_path is required."}], "is_error": True}

    old_string = args.get("old_string") or None
    new_string = args.get("new_string") or None
    new_content = args.get("new_content") or None
    description = (args.get("description") or "agent self-edit").strip()
    replace_all = bool(args.get("replace_all", False))
    restart = bool(args.get("restart", False))

    ok, msg = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _self_edit_mod.apply_edit(
            file_path=file_path,
            old_string=old_string,
            new_string=new_string,
            new_content=new_content,
            description=description,
            replace_all=replace_all,
        ),
    )

    if ok and restart:
        _restart_requested = True
        msg += " Restarting..."

    return {"content": [{"type": "text", "text": msg}], **({"is_error": True} if not ok else {})}


# ── Learning tool ─────────────────────────────────────────────────────────────

_LEARN_CATEGORIES = {"skill", "behavior", "preference", "context"}

@sdk.tool(
    name="learn",
    description=(
        "Permanently encode something the user taught you, or a pattern you noticed, "
        "into the right place so it applies to all future sessions.\n\n"
        "Categories:\n"
        "- 'skill'      → new/updated skill file (hot-loaded, no restart); "
        "use for repeatable workflows, formatting rules, multi-step procedures\n"
        "- 'behavior'   → appended to HOUSE_RULES.md; use for always/never rules "
        "about how you should act\n"
        "- 'preference' → appended to USER_PROFILE.md; use for the user's personal "
        "preferences, working style, communication style\n"
        "- 'context'    → appended to BUSINESS_CONTEXT.md; use for facts about the "
        "business, project, team, or tech stack\n\n"
        "skill_name is required when category='skill' — use a short slug like "
        "'morning-report' or 'hubspot-format'."
    ),
    input_schema={"lesson": str, "category": str, "skill_name": str},
)
async def tool_learn(args: dict) -> dict:
    lesson = (args.get("lesson") or "").strip()
    category = (args.get("category") or "").strip().lower()
    skill_name = (args.get("skill_name") or "").strip()

    if not lesson:
        return {"content": [{"type": "text", "text": "lesson is required."}], "is_error": True}
    if category not in _LEARN_CATEGORIES:
        opts = ", ".join(sorted(_LEARN_CATEGORIES))
        return {"content": [{"type": "text", "text": f"category must be one of: {opts}"}], "is_error": True}

    if category == "skill":
        if not skill_name:
            return {"content": [{"type": "text", "text": "skill_name is required when category='skill'."}], "is_error": True}
        filename = _skills_mod.write_skill(skill_name, lesson)
        return {"content": [{"type": "text", "text": f"Skill saved: {filename}. Active on the next turn."}]}

    # Soul file routing
    soul_file_map = {
        "behavior":   SHARED_DIR / "HOUSE_RULES.md",
        "preference": SHARED_DIR / "USER_PROFILE.md",
        "context":    SHARED_DIR / "BUSINESS_CONTEXT.md",
    }
    target = soul_file_map[category]

    if not target.exists():
        target.write_text(f"# {target.stem}\n\n", encoding="utf-8")

    with target.open("a", encoding="utf-8") as f:
        f.write(f"\n- {lesson}\n")

    # Reindex in memory index if it's tracking this file
    if _mem_index:
        _mem_index.reindex_file(target)

    logger.info("learn: appended to %s", target.name)
    return {"content": [{"type": "text", "text": f"Learned and saved to {target.name}. Active on the next turn."}]}


# ── Background process tool ───────────────────────────────────────────────────

_bg_jobs: dict[str, asyncio.subprocess.Process] = {}

@sdk.tool(
    name="run_bg",
    description=(
        "Run a long shell command in the background without blocking the turn. "
        "Returns immediately with a job_id. "
        "Use 'job_wait' to block until it finishes and get its output, or "
        "'job_status' to poll without blocking. "
        "Ideal for: npm run build, npm install, long tests, server starts. "
        "cwd: working directory for the command (default: project root)."
    ),
    input_schema={"command": str, "cwd": str},
)
async def tool_run_bg(args: dict) -> dict:
    command = args.get("command", "").strip()
    cwd = args.get("cwd", "").strip() or str(ROOT)
    if not command:
        return {"content": [{"type": "text", "text": "command is required."}], "is_error": True}

    job_id = f"job_{int(asyncio.get_event_loop().time() * 1000) % 100000}"
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        _bg_jobs[job_id] = proc
        logger.info("run_bg [%s] PID=%d: %s", job_id, proc.pid, command)
        return {"content": [{"type": "text", "text": f"Started {job_id} (PID {proc.pid}). Use job_wait or job_status to check."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Failed to start: {e}"}], "is_error": True}


@sdk.tool(
    name="job_wait",
    description=(
        "Wait for a background job to finish and return its full output. "
        "Blocks until the job completes (use for jobs expected to finish in seconds). "
        "For jobs that take minutes, use job_status + send_message instead."
    ),
    input_schema={"job_id": str, "timeout": int},
)
async def tool_job_wait(args: dict) -> dict:
    job_id = args.get("job_id", "").strip()
    timeout = int(args.get("timeout") or 120)
    proc = _bg_jobs.get(job_id)
    if not proc:
        return {"content": [{"type": "text", "text": f"Job {job_id!r} not found."}], "is_error": True}
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode(errors="replace").strip() if stdout else ""
        exit_code = proc.returncode
        _bg_jobs.pop(job_id, None)
        status = "✓ exited 0" if exit_code == 0 else f"✗ exited {exit_code}"
        tail = output[-3000:] if len(output) > 3000 else output
        return {"content": [{"type": "text", "text": f"{status}\n\n{tail}"}]}
    except asyncio.TimeoutError:
        return {"content": [{"type": "text", "text": f"Timed out after {timeout}s — job still running. Use job_status to check."}]}


@sdk.tool(
    name="job_status",
    description=(
        "Check whether a background job is still running or has finished. "
        "If finished, returns exit code and last 2000 chars of output. "
        "Non-blocking — returns immediately."
    ),
    input_schema={"job_id": str},
)
async def tool_job_status(args: dict) -> dict:
    job_id = args.get("job_id", "").strip()
    proc = _bg_jobs.get(job_id)
    if not proc:
        return {"content": [{"type": "text", "text": f"Job {job_id!r} not found (may have already completed)."}]}
    if proc.returncode is None:
        return {"content": [{"type": "text", "text": f"Job {job_id} is still running (PID {proc.pid})."}]}
    # Finished — drain output
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    except (asyncio.TimeoutError, Exception):
        stdout = b""
    output = stdout.decode(errors="replace").strip() if stdout else ""
    exit_code = proc.returncode
    _bg_jobs.pop(job_id, None)
    status = "✓ exited 0" if exit_code == 0 else f"✗ exited {exit_code}"
    tail = output[-2000:] if len(output) > 2000 else output
    return {"content": [{"type": "text", "text": f"{status}\n\n{tail}"}]}


# ── Proactive messaging tools ─────────────────────────────────────────────────

@sdk.tool(
    name="send_message",
    description=(
        "Push a message to the user's chat without waiting for them to ask. "
        "Use this to proactively send alerts, status updates, or results — "
        "for example, after completing a long background task, or when a "
        "monitored condition is met. The message goes to the same chat as the "
        "current conversation (Telegram or Discord)."
    ),
    input_schema={"message": str},
)
async def tool_send_message(args: dict) -> dict:
    message = args.get("message", "").strip()
    if not message:
        return {"content": [{"type": "text", "text": "message is required."}], "is_error": True}

    chat_id = _current_chat_id.get()
    if not chat_id or not _app:
        return {"content": [{"type": "text", "text": "No active chat context — cannot send proactively."}], "is_error": True}

    formatted = md_to_html(message)
    for chunk in chunk_text(formatted):
        try:
            await _app.bot.send_message(chat_id, chunk, parse_mode=ParseMode.HTML)
        except Exception:
            try:
                await _app.bot.send_message(chat_id, chunk)
            except Exception as e:
                return {"content": [{"type": "text", "text": f"Failed to send: {e}"}], "is_error": True}

    logger.info("send_message: pushed to chat %d", chat_id)
    return {"content": [{"type": "text", "text": "Message sent."}]}


@sdk.tool(
    name="schedule_once",
    description=(
        "Run a task exactly once at a future time, then discard it. "
        "Use this for one-off reminders, follow-ups, and deferred work. "
        "when_str examples: 'in 30 minutes', 'in 2 hours', 'at 9am', "
        "'at 14:30', 'tomorrow at 9am'."
    ),
    input_schema={"task_prompt": str, "when_str": str},
)
async def tool_schedule_once(args: dict) -> dict:
    task_prompt = args.get("task_prompt", "").strip()
    when_str = args.get("when_str", "").strip()
    if not task_prompt or not when_str:
        return {"content": [{"type": "text", "text": "task_prompt and when_str are required."}], "is_error": True}

    chat_id = _current_chat_id.get()
    if not chat_id:
        return {"content": [{"type": "text", "text": "Cannot determine chat context."}], "is_error": True}

    try:
        fire_at = parse_once(when_str)
    except ValueError as e:
        return {"content": [{"type": "text", "text": str(e)}], "is_error": True}

    if not _app or not _app.job_queue:
        return {"content": [{"type": "text", "text": "Job queue not available."}], "is_error": True}

    task_data = {"chat_id": chat_id, "task_prompt": task_prompt, "id": "once"}
    _app.job_queue.run_once(
        _run_scheduled_task,
        when=fire_at,
        data=task_data,
        name=f"once_{chat_id}_{int(fire_at.timestamp())}",
    )

    fire_str = fire_at.strftime("%Y-%m-%d %H:%M")
    return {"content": [{"type": "text", "text": f"One-shot task scheduled for {fire_str}."}]}


# ── MCP server bundling all tools ─────────────────────────────────────────────
_memory_mcp = sdk.create_sdk_mcp_server(
    name="memory",
    tools=[
        tool_memory_search, tool_memory_write_long_term, tool_memory_write_daily, tool_memory_read_file,
        tool_wiki_write, tool_wiki_read, tool_wiki_list,
        tool_connector_list, tool_connector_add, tool_connector_remove, tool_connector_info,
        tool_skill_list, tool_skill_read, tool_skill_write, tool_skill_delete,
        tool_subagent_list, tool_subagent_create, tool_subagent_run,
        tool_scheduler_add, tool_scheduler_list, tool_scheduler_remove,
        tool_send_message, tool_schedule_once,
        tool_self_edit,
        tool_learn,
        tool_run_bg, tool_job_wait, tool_job_status,
    ],
)


# ── Scheduler helpers ─────────────────────────────────────────────────────────

def _task_schedule_fields(schedule_str: str) -> dict:
    """Parse schedule_str and return {schedule_type, schedule_value}."""
    parsed = parse_schedule(schedule_str)
    return {
        "schedule_type": parsed["type"],
        "schedule_value": str(parsed.get("seconds") or parsed.get("time", "")),
    }


async def _run_scheduled_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue callback — runs a scheduled task and delivers the reply."""
    task: dict = context.job.data
    chat_id: int = task["chat_id"]
    task_prompt: str = task["task_prompt"]
    logger.info("Running scheduled task #%s for chat %d", task["id"], chat_id)
    reply = await run_claude(f"[Scheduled task] {task_prompt}", chat_id)
    formatted = md_to_html(reply)
    for chunk in chunk_text(formatted):
        try:
            await context.bot.send_message(chat_id, chunk, parse_mode=ParseMode.HTML)
        except Exception:
            try:
                await context.bot.send_message(chat_id, chunk)
            except Exception as e:
                logger.warning("Failed to deliver scheduled task result to %d: %s", chat_id, e)


def _register_one_task(app: "Application", task: dict) -> None:
    """Register a single task row with the JobQueue."""
    from telegram.ext import JobQueue
    jq: JobQueue = app.job_queue
    name = f"task_{task['id']}"
    stype = task["schedule_type"]
    svalue = task["schedule_value"]
    if stype == "interval":
        jq.run_repeating(
            _run_scheduled_task,
            interval=int(svalue),
            first=int(svalue),
            data=task,
            name=name,
        )
    elif stype == "daily":
        h, m = svalue.split(":")
        jq.run_daily(
            _run_scheduled_task,
            time=dtime(int(h), int(m)),
            data=task,
            name=name,
        )
    logger.info("Registered scheduled task #%s (%s %s)", task["id"], stype, svalue)


def _register_scheduled_tasks(app: "Application") -> None:
    """Restore all enabled tasks from the DB into the JobQueue at startup."""
    tasks = db_all_enabled_tasks(DB_PATH)
    for task in tasks:
        try:
            _register_one_task(app, task)
        except Exception as e:
            logger.warning("Failed to register task #%s: %s", task["id"], e)
    if tasks:
        logger.info("Restored %d scheduled task(s) from DB", len(tasks))


# ── Instruction loader ─────────────────────────────────────────────────────────
def load_instructions(agent_dir: Path) -> Path:
    """Personal override takes precedence if it exists, otherwise fall back to generic."""
    personal = agent_dir / "CLAUDE.personal.md"
    generic = agent_dir / "CLAUDE.md"
    if personal.exists():
        logger.info("Using personal instructions: %s", personal)
        return personal
    logger.info("Using generic instructions: %s", generic)
    return generic


def build_system_prompt(message: str = "") -> str:
    """
    Injection order:
      1. USER_PROFILE.md
      2. BUSINESS_CONTEXT.md
      3. HOUSE_RULES.md
      4. MEMORY.md  (long-term memory)
      5. memory/today.md  (today's notes)
      6. memory/yesterday.md  (yesterday's notes)
      7. CLAUDE.personal.md or CLAUDE.md
    """
    parts: list[str] = []

    for soul_file in [
        SHARED_DIR / "USER_PROFILE.md",
        SHARED_DIR / "BUSINESS_CONTEXT.md",
        SHARED_DIR / "HOUSE_RULES.md",
    ]:
        if soul_file.exists() and soul_file.stat().st_size > 0:
            parts.append(soul_file.read_text().strip())

    # Long-term memory
    memory_md = WORKSPACE / "MEMORY.md"
    if memory_md.exists() and memory_md.stat().st_size > 0:
        parts.append("## Long-term Memory\n\n" + memory_md.read_text().strip())

    # Daily notes: today and yesterday
    today = date.today()
    for delta, label in [(0, "Today"), (1, "Yesterday")]:
        d = today.replace(day=today.day - delta) if delta == 0 else \
            date.fromordinal(today.toordinal() - delta)
        daily = WORKSPACE / "memory" / f"{d.isoformat()}.md"
        if daily.exists() and daily.stat().st_size > 0:
            parts.append(f"## Daily Notes ({label}, {d.isoformat()})\n\n" + daily.read_text().strip())

    parts.append(load_instructions(AGENT_DIR).read_text().strip())

    skills_text = _skills_mod.load_relevant(message)
    if skills_text:
        parts.append("## Skills\n\n" + skills_text)

    return "\n\n---\n\n".join(parts)


# ── Database ───────────────────────────────────────────────────────────────────
def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
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
            CREATE TABLE IF NOT EXISTS token_usage (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      INTEGER NOT NULL,
                ts           TEXT NOT NULL DEFAULT (datetime('now')),
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_cost_usd REAL
            );
        """)
    init_scheduler_table(DB_PATH)
    init_shared_context_tables(DB_PATH)


def _log_usage(chat_id: int, usage: dict, cost: Optional[float]) -> None:
    input_tok = usage.get("input_tokens", 0)
    output_tok = usage.get("output_tokens", 0)
    logger.info(
        "token_usage chat=%d: %d in / %d out | $%.5f",
        chat_id, input_tok, output_tok, cost or 0,
    )
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO token_usage (chat_id, input_tokens, output_tokens, total_cost_usd)"
            " VALUES (?, ?, ?, ?)",
            (chat_id, input_tok, output_tok, cost),
        )


def db_get_session(chat_id: int) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT session_id FROM sessions WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return row[0] if row else None


def db_save_session(chat_id: int, session_id: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT INTO sessions (chat_id, session_id, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET session_id=excluded.session_id,
               updated_at=excluded.updated_at""",
            (chat_id, session_id),
        )


def db_delete_session(chat_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))


def db_log(chat_id: int, role: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )


def upsert_user(update: Update) -> None:
    """Record the sender in user_registry so they can be resolved by name for sharing.

    Must only be called after is_allowed(update) returns True.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    if user is None or chat_id is None:
        return
    db_upsert_user(DB_PATH, chat_id, user.id, user.username, user.full_name)


# ── Allowlist ──────────────────────────────────────────────────────────────────
def is_allowed(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    if user_id is None or chat_id is None:
        return False
    is_dm = chat_id == user_id
    if is_dm:
        return user_id in ALLOWED_USER_IDS
    return user_id in ALLOWED_USER_IDS and chat_id in ALLOWED_CHAT_IDS


# ── Markdown → Telegram HTML ──────────────────────────────────────────────────

def _format_table(rows: list[list[str]]) -> str:
    """Render a list of cell-rows as a fixed-width monospace table."""
    if not rows:
        return ""
    col_count = max(len(r) for r in rows)
    # Normalise all rows to the same column count
    rows = [r + [""] * (col_count - len(r)) for r in rows]
    col_widths = [max(len(r[c]) for r in rows) for c in range(col_count)]
    sep = "  ".join("─" * w for w in col_widths)
    lines = []
    for idx, row in enumerate(rows):
        lines.append("  ".join(cell.ljust(col_widths[c]) for c, cell in enumerate(row)).rstrip())
        if idx == 0:
            lines.append(sep)
    return "\n".join(lines)


def md_to_html(text: str) -> str:
    result = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(html.escape(lines[i], quote=False))
                i += 1
            code_body = "\n".join(code_lines)
            if lang:
                result.append(f'<pre><code class="language-{html.escape(lang)}">{code_body}</code></pre>')
            else:
                result.append(f"<pre>{code_body}</pre>")
            i += 1
            continue

        # Markdown table (pipe-delimited with separator row)
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|[-| :]+\|\s*$", lines[i + 1]):
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i]:
                if not re.match(r"^\s*\|[-| :]+\|\s*$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            result.append("<pre>" + html.escape(_format_table(rows), quote=False) + "</pre>")
            continue

        # Standalone bold line (e.g. **Phase 3 — …**) → treat as heading with spacing
        m = re.match(r"^\*\*(.+?)\*\*\s*$", line)
        if m:
            if result and result[-1] != "":
                result.append("")
            result.append("<b>" + _inline(m.group(1)) + "</b>")
            i += 1
            continue

        # Heading → bold, with blank line before for visual separation
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            if result and result[-1] != "":
                result.append("")
            result.append("<b>" + _inline(m.group(2)) + "</b>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            result.append("─────────────────────")
            i += 1
            continue

        # Blockquote
        m = re.match(r"^>\s*(.*)", line)
        if m:
            result.append("<i>" + _inline(m.group(1)) + "</i>")
            i += 1
            continue

        # Unordered list item — supports up to 3 levels of nesting
        m = re.match(r"^(\s{0,8})[-*+]\s+(.*)", line)
        if m:
            depth = len(m.group(1)) // 2
            prefix = "  " * depth + ("◦" if depth > 0 else "•")
            result.append(f"{prefix} {_inline(m.group(2))}")
            i += 1
            continue

        # Ordered list item — supports up to 3 levels of nesting
        m = re.match(r"^(\s{0,8})(\d+)\.\s+(.*)", line)
        if m:
            depth = len(m.group(1)) // 2
            prefix = "  " * depth + m.group(2) + "."
            result.append(f"{prefix} {_inline(m.group(3))}")
            i += 1
            continue

        # Regular line (blank lines preserved → paragraph spacing in Telegram)
        result.append(_inline(line))
        i += 1

    return "\n".join(result)


_INLINE_RE = re.compile(
    r"`(?P<code>[^`\n]+)`"
    r"|(?:\*\*|__)(?P<bold>(?:\*(?!\*)|[^*])*?)(?:\*\*|__)"
    r"|\*(?P<italic>[^*\n]+)\*"
    r"|(?<!\w)_(?P<italic2>[^_\n]+)_(?!\w)"
    r"|~~(?P<strike>.+?)~~"
    r"|\[(?P<link_text>[^\]]+)\]\((?P<link_url>https?://[^)]+)\)"
)


def _inline(text: str) -> str:
    result = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            result.append(html.escape(text[pos:m.start()], quote=False))
        if m.group("code") is not None:
            result.append(f"<code>{html.escape(m.group('code'), quote=False)}</code>")
        elif m.group("bold") is not None:
            result.append(f"<b>{_inline(m.group('bold'))}</b>")
        elif m.group("italic") is not None:
            result.append(f"<i>{html.escape(m.group('italic'), quote=False)}</i>")
        elif m.group("italic2") is not None:
            result.append(f"<i>{html.escape(m.group('italic2'), quote=False)}</i>")
        elif m.group("strike") is not None:
            result.append(f"<s>{html.escape(m.group('strike'), quote=False)}</s>")
        elif m.group("link_text") is not None:
            result.append(f'<a href="{html.escape(m.group("link_url"))}">{html.escape(m.group("link_text"), quote=False)}</a>')
        pos = m.end()
    if pos < len(text):
        result.append(html.escape(text[pos:], quote=False))
    return "".join(result)


# ── Message chunker ────────────────────────────────────────────────────────────
def chunk_text(text: str, max_len: int = TG_MAX_CHARS) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        remaining = text[pos:]
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        slice_ = text[pos : pos + max_len]
        cut = slice_.rfind("\n\n")
        if cut == -1:
            cut = slice_.rfind("\n")
        if cut == -1:
            cut = slice_.rfind(" ")
        if cut <= 0:
            cut = max_len
        else:
            cut += 1
        chunks.append(text[pos : pos + cut].strip())
        pos += cut
    return [c for c in chunks if c]


# ── Claude query ───────────────────────────────────────────────────────────────
async def _warn_slow_request(chat_id: int, delay: float) -> None:
    """Fire a heads-up message delay seconds into a long-running request."""
    await asyncio.sleep(delay)
    if not _app:
        return
    try:
        remaining = CLAUDE_TIMEOUT - int(delay)
        await _app.bot.send_message(
            chat_id,
            f"⏳ Still working... this is taking a while. "
            f"If no response arrives in ~{remaining}s the request will be cancelled automatically. "
            "For complex tasks, try breaking them into smaller steps.",
        )
    except Exception:
        pass


async def run_claude(prompt: str, chat_id: int, silent: bool = False) -> str:
    """Collect all streamed text blocks into one string. Use for non-interactive callers."""
    parts = []
    async for text in stream_claude(prompt, chat_id, silent=silent):
        parts.append(text)
    reply = "\n\n".join(parts).strip()
    if silent and reply == "NO_REPLY":
        return ""
    return reply or "(no response)"


async def stream_claude(prompt: str, chat_id: int, silent: bool = False, _attempt: int = 0):
    """
    Async generator — yields each assistant text block as Claude produces it.
    Use in interactive handlers for progressive Telegram delivery.
    silent=True suppresses NO_REPLY (used for flush turns).
    """
    _current_chat_id.set(chat_id)

    # Inject any unacknowledged shared context as a system note
    shared = db_get_unacknowledged_shared(DB_PATH, chat_id)
    if shared:
        note = format_shared_note(shared)
        prompt = (
            f"[System: The following context was shared with you by other users]\n"
            f"{note}\n"
            f"---\n\n"
            f"{prompt}"
        )
        db_mark_acknowledged(DB_PATH, chat_id)

    session_id = db_get_session(chat_id)
    system_prompt = build_system_prompt(prompt)

    options = sdk.ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        system_prompt=system_prompt,
        cwd=str(WORKSPACE),
        resume=session_id,
        permission_mode="bypassPermissions",
        setting_sources=["user"],
        mcp_servers={"memory": _memory_mcp},
        allowed_tools=_build_allowed_tools(),
    )

    new_session_id: Optional[str] = None
    reply_parts: list[str] = []

    _warn_delay = max(CLAUDE_TIMEOUT - 60, CLAUDE_TIMEOUT // 2)
    _warn_task = asyncio.create_task(_warn_slow_request(chat_id, _warn_delay))
    try:
        async with asyncio.timeout(CLAUDE_TIMEOUT):
            async for event in sdk.query(prompt=prompt, options=options):
                if isinstance(event, sdk.AssistantMessage):
                    msg_text = "".join(
                        block.text for block in event.content
                        if isinstance(block, sdk.TextBlock)
                    )
                    if msg_text.strip():
                        reply_parts.append(msg_text)
                        yield msg_text
                    if event.session_id:
                        new_session_id = event.session_id
                elif isinstance(event, sdk.ResultMessage):
                    if event.session_id:
                        new_session_id = event.session_id
                    if event.usage:
                        _log_usage(chat_id, event.usage, event.total_cost_usd)
    except TimeoutError:
        logger.error(
            "Claude query timed out after %ds for chat %d — subprocess killed",
            CLAUDE_TIMEOUT, chat_id,
        )
        yield f"⏱ Request timed out after {CLAUDE_TIMEOUT // 60} minutes. The process was killed. Try again or break your request into smaller steps."
        return
    except sdk.CLINotFoundError:
        logger.error("claude CLI not found")
        yield "Error: claude CLI not found. Make sure `claude` is installed and authenticated."
        return
    except sdk.CLIConnectionError as e:
        logger.error("Claude connection error: %s", e)
        db_delete_session(chat_id)
        yield "Connection error — session reset. Please try again."
        return
    except Exception as e:
        if "Control request timeout: initialize" in str(e) and _attempt == 0:
            logger.warning(
                "Initialize timeout for chat %d — resetting session and retrying",
                chat_id,
            )
            db_delete_session(chat_id)
            async for text in stream_claude(prompt, chat_id, silent=silent, _attempt=1):
                yield text
            return
        logger.exception("Unexpected error from Claude: %s", e)
        yield f"Error: {e}"
        return
    finally:
        _warn_task.cancel()

    if new_session_id:
        db_save_session(chat_id, new_session_id)

    if silent and "\n\n".join(reply_parts).strip() == "NO_REPLY":
        return


# ── Pre-compaction flush ───────────────────────────────────────────────────────
async def maybe_flush(chat_id: int) -> None:
    """Fire a silent flush turn if the session is approaching context limits."""
    if not _flush_mgr.needs_flush(chat_id):
        return
    logger.info("Flushing memory for chat %d before compaction", chat_id)
    today = date.today().isoformat()
    flush_prompt = _flush_mgr.flush_prompt(today)
    reply = await run_claude(flush_prompt, chat_id, silent=True)
    _flush_mgr.reset(chat_id)
    if reply:
        logger.info("Flush produced output: %s...", reply[:60])


# ── MCP readiness probe ────────────────────────────────────────────────────────

async def _probe_mcp() -> None:
    """
    Run a silent one-turn query to force the SDK to initialize all MCP server
    connections. Sets _mcp_ready_event when done (or on error) so handle_message
    can proceed.
    """
    global _mcp_ready_event
    logger.info("MCP probe: initialising connections...")
    try:
        options = sdk.ClaudeAgentOptions(
            cwd=str(WORKSPACE),
            permission_mode="bypassPermissions",
            setting_sources=["user"],
            mcp_servers={"memory": _memory_mcp},
            allowed_tools=_build_allowed_tools(),
        )
        async for event in sdk.query(prompt="Reply with the single word READY.", options=options):
            if isinstance(event, sdk.ResultMessage):
                break
        logger.info("MCP probe: all connections ready")
    except Exception as e:
        logger.warning("MCP probe failed (non-fatal): %s", e)
    finally:
        if _mcp_ready_event:
            _mcp_ready_event.set()


# ── Handlers ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text("Main is online. Send me anything.")


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"<b>User ID:</b> <code>{user.id}</code>\n"
        f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
        f"<b>Username:</b> @{user.username or '—'}\n"
        f"<b>Name:</b> {user.full_name}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    db_delete_session(chat_id)
    _flush_mgr.reset(chat_id)
    await update.message.reply_text("Session reset. Next message starts a fresh conversation.")


def _do_restart() -> None:
    """Restart this process. Prefers systemd; falls back to os.execv."""
    if shutil.which("systemctl"):
        try:
            subprocess.Popen(
                ["systemctl", "--user", "restart", "claude-main.service"],
                start_new_session=True,
            )
            return
        except Exception:
            pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text("Restarting...")
    await asyncio.sleep(0.5)
    _do_restart()


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    uptime_secs = int(time.time() - _start_time)
    hours, rem = divmod(uptime_secs, 3600)
    minutes, seconds = divmod(rem, 60)

    with sqlite3.connect(DB_PATH) as con:
        session_count = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        task_count = con.execute("SELECT COUNT(*) FROM scheduled_tasks WHERE enabled = 1").fetchone()[0]
        today_usage = con.execute(
            "SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0),"
            " COALESCE(SUM(total_cost_usd),0) FROM token_usage WHERE date(ts)=date('now')"
        ).fetchone()
        total_usage = con.execute(
            "SELECT COALESCE(SUM(total_cost_usd),0) FROM token_usage"
        ).fetchone()

    memory_md = WORKSPACE / "MEMORY.md"
    memory_size = memory_md.stat().st_size if memory_md.exists() else 0
    today_note = WORKSPACE / "memory" / f"{date.today().isoformat()}.md"
    today_size = today_note.stat().st_size if today_note.exists() else 0

    today_in, today_out, today_cost = today_usage
    total_cost = total_usage[0]

    await update.message.reply_text(
        f"<b>Main status</b>\n"
        f"Uptime: {hours}h {minutes}m {seconds}s\n"
        f"Active sessions: {session_count}\n"
        f"Scheduled tasks: {task_count}\n"
        f"MEMORY.md: {memory_size:,} bytes\n"
        f"Today's notes: {today_size:,} bytes\n"
        f"\n<b>Token usage (today)</b>\n"
        f"Input: {today_in:,} | Output: {today_out:,}\n"
        f"Today cost: ${today_cost:.4f}\n"
        f"Total cost: ${total_cost:.4f}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /share @username <content>   or   /share Name: <content>

    Shares content with the resolved user and sends them a push notification.
    Must only be called after is_allowed returns True.
    """
    if not update.message or not is_allowed(update):
        return
    upsert_user(update)

    chat_id = update.effective_chat.id
    text = update.message.text or ""

    # Strip the /share command prefix (handles /share@botname form in group chats)
    body = re.sub(r"^/share(?:@\S+)?", "", text, count=1).strip()
    if not body:
        await update.message.reply_text(
            "Usage: /share @username <content>\n"
            "Example: /share @jay here's what we decided about the API"
        )
        return

    # Parse target: @username or "Name:" prefix
    m = re.match(r"^(@\S+|[\w][\w\s]*?)[:]\s+(.+)$", body, re.DOTALL)
    if not m:
        # Try "@handle content" form (no colon)
        m2 = re.match(r"^(@\S+)\s+(.+)$", body, re.DOTALL)
        if not m2:
            await update.message.reply_text(
                "Usage: /share @username <content>  or  /share Name: <content>"
            )
            return
        target_raw, content = m2.group(1), m2.group(2).strip()
    else:
        target_raw, content = m.group(1), m.group(2).strip()

    try:
        result = db_resolve_user(DB_PATH, target_raw)
    except ValueError:
        await update.message.reply_text(
            f"'{target_raw}' matches multiple users. Use a more specific name or @username."
        )
        return

    if result is None:
        await update.message.reply_text(
            f"No user found matching '{target_raw}'. "
            "They need to have messaged the bot at least once."
        )
        return

    to_chat_id, to_name = result
    if to_chat_id == chat_id:
        await update.message.reply_text("You can't share context with yourself.")
        return

    from_name = update.effective_user.full_name or str(chat_id)
    db_share_context(DB_PATH, from_chat_id=chat_id, to_chat_id=to_chat_id, content=content)

    # Push notification to recipient
    push_text = f"📤 <b>{html.escape(from_name, quote=False)}</b> shared something with you:\n{html.escape(content, quote=False)}"
    push_failed = False
    try:
        await context.bot.send_message(to_chat_id, push_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning("Could not push share notification to %d: %s", to_chat_id, e)
        push_failed = True

    notice = " (note: could not send them a notification)" if push_failed else ""
    await update.message.reply_text(f"Shared with {to_name or str(to_chat_id)}.{notice}")


async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /revoke @username <content or label>

    Soft-deletes matching shared context and notifies recipient.
    """
    if not update.message or not is_allowed(update):
        return
    upsert_user(update)

    chat_id = update.effective_chat.id
    text = update.message.text or ""
    body = re.sub(r"^/revoke(?:@\S+)?", "", text, count=1).strip()

    if not body:
        await update.message.reply_text(
            "Usage: /revoke @username <content hint>\n"
            "Example: /revoke @jay API decision"
        )
        return

    m = re.match(r"^(@\S+|[\w][\w\s]*?)[:\s]\s*(.+)$", body, re.DOTALL)
    if not m:
        await update.message.reply_text(
            "Usage: /revoke @username <content hint>"
        )
        return

    target_raw, content_hint = m.group(1), m.group(2).strip()

    try:
        result = db_resolve_user(DB_PATH, target_raw)
    except ValueError:
        await update.message.reply_text(
            f"'{target_raw}' matches multiple users. Use a more specific name or @username."
        )
        return

    if result is None:
        await update.message.reply_text(f"No user found matching '{target_raw}'.")
        return

    to_chat_id, to_name = result
    if to_chat_id == chat_id:
        await update.message.reply_text("You don't have any shared context with yourself.")
        return

    from_name = (update.effective_user.full_name if update.effective_user else None) or str(chat_id)

    revoked_ids = db_revoke_shared(
        DB_PATH, from_chat_id=chat_id, to_chat_id=to_chat_id, content_hint=content_hint
    )

    if not revoked_ids:
        await update.message.reply_text(
            f"No matching shared context found for '{content_hint}'."
        )
        return

    # Notify recipient
    snippet = content_hint[:80]
    notif = (
        f"🚫 <b>{html.escape(from_name, quote=False)}</b> revoked shared context: "
        f"<i>{html.escape(snippet, quote=False)}</i>"
    )
    push_failed = False
    try:
        await context.bot.send_message(to_chat_id, notif, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning("Could not send revoke notification to %d: %s", to_chat_id, e)
        push_failed = True

    notice = " (could not send them a notification)" if push_failed else ""
    await update.message.reply_text(
        f"Revoked {len(revoked_ids)} item(s) shared with {to_name or str(to_chat_id)}.{notice}"
    )


async def cmd_shared(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pull all shared context on demand."""
    if not update.message or not is_allowed(update):
        return
    upsert_user(update)
    await _handle_pull(update, context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    task = _active_tasks.get(chat_id)
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("⛔ Cancelled.")
    else:
        await update.message.reply_text("Nothing is running right now.")


def _track_task(chat_id: int) -> None:
    t = asyncio.current_task()
    if t:
        _active_tasks[chat_id] = t


def _untrack_task(chat_id: int) -> None:
    _active_tasks.pop(chat_id, None)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    if not is_allowed(update):
        return
    upsert_user(update)

    if _mcp_ready_event and not _mcp_ready_event.is_set():
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        try:
            await asyncio.wait_for(asyncio.shield(_mcp_ready_event.wait()), timeout=_MCP_PROBE_TIMEOUT)
        except asyncio.TimeoutError:
            _mcp_ready_event.set()

    chat_id = update.effective_chat.id
    _track_task(chat_id)
    photo = update.message.photo[-1]  # highest resolution
    caption = update.message.caption or ""

    media_dir = WORKSPACE / "media"
    photo_path = await _media_mod.save_photo(context.bot, photo.file_id, media_dir)

    prompt = (
        f"The user sent a photo. Analyze it using the Read tool at path: {photo_path}"
        + (f"\nTheir caption: {caption}" if caption else "")
    )
    log_entry = f"[photo]{f' — {caption}' if caption else ''}"
    db_log(chat_id, "user", log_entry)
    _flush_mgr.record(chat_id, prompt)

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    try:
        async for text in stream_claude(prompt, chat_id):
            typing_task.cancel()
            db_log(chat_id, "assistant", text)
            _flush_mgr.record(chat_id, text)
            for chunk in chunk_text(md_to_html(text)):
                try:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                except Exception:
                    await update.message.reply_text(chunk)
            typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    except asyncio.CancelledError:
        pass
    finally:
        typing_task.cancel()
        _untrack_task(chat_id)

    if _restart_requested:
        await asyncio.sleep(1)
        _do_restart()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not is_allowed(update):
        return
    upsert_user(update)
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    if _mcp_ready_event and not _mcp_ready_event.is_set():
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        try:
            await asyncio.wait_for(asyncio.shield(_mcp_ready_event.wait()), timeout=_MCP_PROBE_TIMEOUT)
        except asyncio.TimeoutError:
            _mcp_ready_event.set()

    chat_id = update.effective_chat.id
    _track_task(chat_id)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    transcript = await _media_mod.transcribe_voice(context.bot, voice.file_id)
    db_log(chat_id, "user", f"[voice] {transcript}")
    _flush_mgr.record(chat_id, transcript)

    typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    try:
        async for text in stream_claude(f"[Voice message transcript]: {transcript}", chat_id):
            typing_task.cancel()
            db_log(chat_id, "assistant", text)
            _flush_mgr.record(chat_id, text)
            for chunk in chunk_text(md_to_html(text)):
                try:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                except Exception:
                    await update.message.reply_text(chunk)
            typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    except asyncio.CancelledError:
        pass
    finally:
        typing_task.cancel()
        _untrack_task(chat_id)

    if _restart_requested:
        await asyncio.sleep(1)
        _do_restart()


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document:
        return
    if not is_allowed(update):
        return
    upsert_user(update)

    if _mcp_ready_event and not _mcp_ready_event.is_set():
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        try:
            await asyncio.wait_for(asyncio.shield(_mcp_ready_event.wait()), timeout=_MCP_PROBE_TIMEOUT)
        except asyncio.TimeoutError:
            _mcp_ready_event.set()

    chat_id = update.effective_chat.id
    _track_task(chat_id)
    doc = update.message.document
    filename = doc.file_name or f"file_{doc.file_id[:12]}"
    caption = update.message.caption or ""

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    media_dir = WORKSPACE / "media"
    saved_path = await _media_mod.save_document(context.bot, doc.file_id, filename, media_dir)

    file_text, is_extractable = _media_mod.extract_text(saved_path)

    if is_extractable:
        prompt = (
            f"The user sent a file: {filename}\n"
            f"Saved at: {saved_path}\n"
            f"Contents:\n\n{file_text}"
            + (f"\n\nTheir note: {caption}" if caption else "")
        )
    else:
        prompt = (
            f"The user sent a file: {filename}\n"
            f"Saved at: {saved_path}\n"
            f"Note: {file_text}"
            + (f"\nTheir note: {caption}" if caption else "")
        )

    db_log(chat_id, "user", f"[document: {filename}]{f' — {caption}' if caption else ''}")
    _flush_mgr.record(chat_id, prompt)

    typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    try:
        async for text in stream_claude(prompt, chat_id):
            typing_task.cancel()
            db_log(chat_id, "assistant", text)
            _flush_mgr.record(chat_id, text)
            for chunk in chunk_text(md_to_html(text)):
                try:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                except Exception:
                    await update.message.reply_text(chunk)
            typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    except asyncio.CancelledError:
        pass
    finally:
        typing_task.cancel()
        _untrack_task(chat_id)

    if _restart_requested:
        await asyncio.sleep(1)
        _do_restart()


_PULL_PATTERNS = [
    r"shared with me",
    r"what did .{1,30} share",
    r"show shared",
    r"shared context",
    r"anything shared",
]
_PULL_RE = re.compile("|".join(_PULL_PATTERNS), re.IGNORECASE)


def _is_pull_request(text: str) -> bool:
    return bool(_PULL_RE.search(text))


async def _handle_pull(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all shared context for this user and inject it into their Claude session."""
    chat_id = update.effective_chat.id
    items = db_list_shared(DB_PATH, to_chat_id=chat_id)

    if not items:
        await update.message.reply_text("Nothing has been shared with you yet.")
        return

    # Group by sender (stable by chat_id; from_name used only for display)
    grouped: dict[int, dict] = {}
    for item in items:
        cid = item["from_chat_id"]
        if cid not in grouped:
            grouped[cid] = {"name": item["from_name"], "items": []}
        grouped[cid]["items"].append(item)

    lines = ["📥 <b>Shared with you:</b>\n"]
    for sender in grouped.values():
        sender_items = sender["items"]
        from_name = sender["name"]
        lines.append(f"<b>From {html.escape(from_name, quote=False)}</b> ({len(sender_items)} item(s))")
        for item in sender_items:
            date_str = item["shared_at"][:10]
            lines.append(f"  • <i>({date_str})</i> {html.escape(item['content'], quote=False)}")
        lines.append("")

    formatted = "\n".join(lines).strip()
    await update.message.reply_text(formatted, parse_mode=ParseMode.HTML)
    db_mark_acknowledged(DB_PATH, chat_id)

    # Inject into Claude session so the AI knows about it
    note = format_shared_note(items)
    inject_prompt = (
        f"[System: The user just pulled their shared context. Inject into your awareness.]\n"
        f"{note}\n"
        f"---\n\n"
        f"The user asked to see their shared context. I've shown them the list above. "
        f"Acknowledge briefly."
    )
    await maybe_flush(chat_id)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    try:
        reply = await run_claude(inject_prompt, chat_id)
    finally:
        typing_task.cancel()

    db_log(chat_id, "assistant", reply)
    _flush_mgr.record(chat_id, reply)

    if reply and reply != "(no response)":
        for chunk in chunk_text(md_to_html(reply)):
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception:
                await update.message.reply_text(chunk)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if not is_allowed(update):
        return
    upsert_user(update)

    # Wait for MCP connections to initialise after startup/restart
    if _mcp_ready_event and not _mcp_ready_event.is_set():
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.TYPING
            )
        except Exception:
            pass
        try:
            await asyncio.wait_for(
                asyncio.shield(_mcp_ready_event.wait()), timeout=_MCP_PROBE_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning("MCP probe timed out — proceeding without guarantee")
            _mcp_ready_event.set()

    chat_id = update.effective_chat.id

    # Reject new messages while Claude is already processing for this chat
    if chat_id in _active_tasks and not _active_tasks[chat_id].done():
        await update.message.reply_text("⏳ Still processing your previous message. Send /stop to cancel it first.")
        return

    _track_task(chat_id)
    user_text = update.message.text
    db_log(chat_id, "user", user_text)
    _flush_mgr.record(chat_id, user_text)

    # Handle pull requests before passing to Claude
    if _is_pull_request(user_text):
        _untrack_task(chat_id)
        await _handle_pull(update, context)
        return

    # Fire flush turn if we're near the context limit (transparent to user)
    await maybe_flush(chat_id)

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass
    typing_task = asyncio.create_task(_keep_typing(context, chat_id))

    try:
        async for text in stream_claude(user_text, chat_id):
            typing_task.cancel()

            db_log(chat_id, "assistant", text)
            _flush_mgr.record(chat_id, text)

            for chunk in chunk_text(md_to_html(text)):
                try:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                except Exception:
                    await update.message.reply_text(chunk)

            typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    except asyncio.CancelledError:
        pass
    finally:
        typing_task.cancel()
        _untrack_task(chat_id)

    if _restart_requested:
        await asyncio.sleep(1)
        _do_restart()


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    try:
        while True:
            await asyncio.sleep(4)
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                pass
    except asyncio.CancelledError:
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception in handler", exc_info=context.error)


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    global _mem_index, _app

    init_db()
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "memory").mkdir(exist_ok=True)
    (WORKSPACE / "sessions").mkdir(exist_ok=True)
    (WORKSPACE / "wiki").mkdir(exist_ok=True)

    # Seed memory files so they always exist for appending
    for seed in [WORKSPACE / "MEMORY.md", WORKSPACE / "DREAMS.md"]:
        seed.touch(exist_ok=True)
    today_note = WORKSPACE / "memory" / f"{date.today().isoformat()}.md"
    if not today_note.exists():
        today_note.write_text(f"# {date.today().isoformat()}\n\n", encoding="utf-8")

    # Build memory index and start file watcher
    _mem_index = MemoryIndex(WORKSPACE)
    _mem_index.build()
    _mem_index.start_watcher()

    instruction_file = load_instructions(AGENT_DIR)
    logger.info("Starting Main — instructions: %s", instruction_file.name)
    logger.info("Allowed user IDs: %s", ALLOWED_USER_IDS)
    logger.info("Memory index ready — watcher running")

    async def _post_init(app: Application) -> None:
        global _mcp_ready_event
        _mcp_ready_event = asyncio.Event()

        # Restore scheduled tasks into the JobQueue
        _register_scheduled_tasks(app)

        installed = get_installed_connectors()
        if installed:
            connector_str = "Connectors: " + ", ".join(installed)
            notice = f"Main is online. {connector_str} — loading..."
        else:
            notice = "Main is online."
            _mcp_ready_event.set()  # no connectors to probe

        for uid in ALLOWED_USER_IDS:
            try:
                await app.bot.send_message(uid, notice)
            except Exception as e:
                logger.warning("Startup notification failed for %d: %s", uid, e)

        if installed:
            asyncio.create_task(_probe_mcp())

        # Start Discord bot if configured
        discord_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        if discord_token:
            _raw_discord_users = os.getenv("DISCORD_ALLOWED_USER_IDS", "")
            _raw_discord_guilds = os.getenv("DISCORD_ALLOWED_GUILD_IDS", "")
            discord_user_ids: set[int] = {
                int(x.strip()) for x in _raw_discord_users.split(",") if x.strip()
            }
            discord_guild_ids: set[int] = {
                int(x.strip()) for x in _raw_discord_guilds.split(",") if x.strip()
            }
            asyncio.create_task(
                _discord_mod.start_discord(discord_token, run_claude, discord_user_ids, discord_guild_ids)
            )
            logger.info("Discord bot task started")

    _app = app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(_post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("stop", cmd_cancel))
    app.add_handler(CommandHandler("share", cmd_share))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(CommandHandler("shared", cmd_shared))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Polling for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
