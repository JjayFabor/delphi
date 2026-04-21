"""
agents/main/agent.py — Main bot runner.

One Telegram bot, one Claude agent, full session persistence.
Each inbound message streams through the Claude Agent SDK and replies
are sent back as chunked Telegram messages.
"""

import asyncio
import logging
import os
import sqlite3
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

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

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[handler, logging.StreamHandler()],
)
logger = logging.getLogger("main")

load_dotenv(ROOT / ".env")

# ── Config ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN_MAIN"]

_raw_user_ids = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {
    int(x.strip()) for x in _raw_user_ids.split(",") if x.strip()
}

_raw_chat_ids = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: set[int] = {
    int(x.strip()) for x in _raw_chat_ids.split(",") if x.strip()
}

TG_MAX_CHARS = 4000  # Telegram limit is 4096; leave headroom


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


def build_system_prompt() -> str:
    """Concatenate soul files + instruction file into a single system prompt string."""
    parts: list[str] = []

    for soul_file in [
        SHARED_DIR / "USER_PROFILE.md",
        SHARED_DIR / "BUSINESS_CONTEXT.md",
        SHARED_DIR / "HOUSE_RULES.md",
    ]:
        if soul_file.exists():
            parts.append(soul_file.read_text().strip())

    instruction_file = load_instructions(AGENT_DIR)
    parts.append(instruction_file.read_text().strip())

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
        """)


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


# ── Allowlist ──────────────────────────────────────────────────────────────────
def is_allowed(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    if user_id is None or chat_id is None:
        return False

    is_dm = chat_id == user_id  # private chat: chat_id == user_id

    if is_dm:
        return user_id in ALLOWED_USER_IDS

    # Group or channel: both user and chat must be in their respective lists
    return user_id in ALLOWED_USER_IDS and chat_id in ALLOWED_CHAT_IDS


# ── Message chunker ────────────────────────────────────────────────────────────
def chunk_text(text: str, max_len: int = TG_MAX_CHARS) -> list[str]:
    """Split text at paragraph or line boundaries to stay under max_len."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        remaining = text[pos:]
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        # Try to cut at a paragraph boundary first, then newline, then space
        slice_ = text[pos : pos + max_len]
        cut = slice_.rfind("\n\n")
        if cut == -1:
            cut = slice_.rfind("\n")
        if cut == -1:
            cut = slice_.rfind(" ")
        if cut <= 0:
            cut = max_len  # hard cut as last resort
        else:
            cut += 1  # include the separator in the left chunk
        chunks.append(text[pos : pos + cut].strip())
        pos += cut

    return [c for c in chunks if c]


# ── Claude query ───────────────────────────────────────────────────────────────
async def run_claude(prompt: str, chat_id: int) -> str:
    """Run one Claude turn. Returns the final text reply."""
    session_id = db_get_session(chat_id)
    system_prompt = build_system_prompt()

    options = sdk.ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(WORKSPACE),
        session_id=session_id,
        continue_conversation=session_id is not None,
    )

    reply_parts: list[str] = []
    new_session_id: Optional[str] = None

    try:
        async for event in sdk.query(prompt=prompt, options=options):
            if isinstance(event, sdk.AssistantMessage):
                for block in event.content:
                    if isinstance(block, sdk.TextBlock):
                        reply_parts.append(block.text)
                if event.session_id:
                    new_session_id = event.session_id
            elif isinstance(event, sdk.ResultMessage):
                if event.session_id:
                    new_session_id = event.session_id
    except sdk.CLINotFoundError:
        logger.error("claude CLI not found — is it installed and on PATH?")
        return "Error: claude CLI not found. Make sure `claude` is installed and authenticated."
    except sdk.CLIConnectionError as e:
        logger.error("Claude connection error: %s", e)
        # Drop stale session and let next message start fresh
        db_delete_session(chat_id)
        return "Connection error — session reset. Please try again."
    except Exception as e:
        logger.exception("Unexpected error from Claude: %s", e)
        return f"Error: {e}"

    if new_session_id:
        db_save_session(chat_id, new_session_id)

    return "".join(reply_parts).strip() or "(no response)"


# ── Handlers ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "Main is online. Send me anything.",
        parse_mode=ParseMode.HTML,
    )


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
    await update.message.reply_text("Session reset. Next message starts a fresh conversation.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text
    db_log(chat_id, "user", user_text)

    # Send typing indicator while Claude works
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Keep typing indicator alive during long runs
    typing_task = asyncio.create_task(_keep_typing(context, chat_id))

    try:
        reply = await run_claude(user_text, chat_id)
    finally:
        typing_task.cancel()

    db_log(chat_id, "assistant", reply)

    for chunk in chunk_text(reply):
        await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Resend typing action every 4 seconds until cancelled."""
    try:
        while True:
            await asyncio.sleep(4)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except asyncio.CancelledError:
        pass


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    init_db()
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "memory").mkdir(exist_ok=True)
    (WORKSPACE / "sessions").mkdir(exist_ok=True)

    instruction_file = load_instructions(AGENT_DIR)
    logger.info("Starting Main — instructions: %s", instruction_file.name)
    logger.info("Allowed user IDs: %s", ALLOWED_USER_IDS)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
