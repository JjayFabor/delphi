"""
agents/main/shared_context.py — Shared context between bot users.

All functions accept db_path as first argument (same pattern as scheduler.py).
"""
import sqlite3
from pathlib import Path
from typing import Optional


def init_shared_context_tables(db_path: Path) -> None:
    with sqlite3.connect(db_path) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS user_registry (
                chat_id   INTEGER PRIMARY KEY,
                user_id   INTEGER,
                username  TEXT,
                full_name TEXT,
                last_seen TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS shared_context (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                from_chat_id INTEGER NOT NULL,
                to_chat_id   INTEGER NOT NULL,
                content      TEXT NOT NULL,
                label        TEXT,
                shared_at    TEXT NOT NULL DEFAULT (datetime('now')),
                acknowledged INTEGER NOT NULL DEFAULT 0,
                revoked      INTEGER NOT NULL DEFAULT 0
            );
        """)


def db_upsert_user(
    db_path: Path,
    chat_id: int,
    user_id: int,
    username: Optional[str],
    full_name: Optional[str],
) -> None:
    """Insert or update a user in user_registry. Updates all fields and last_seen on conflict."""
    with sqlite3.connect(db_path) as con:
        con.execute(
            """INSERT INTO user_registry (chat_id, user_id, username, full_name, last_seen)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET
                   user_id=excluded.user_id,
                   username=excluded.username,
                   full_name=excluded.full_name,
                   last_seen=excluded.last_seen""",
            (chat_id, user_id, username, full_name),
        )


def db_resolve_user(db_path: Path, name: str) -> Optional[tuple[int, Optional[str]]]:
    """
    Resolve a name/username to (chat_id, full_name).
    Priority 1: exact username match (case-insensitive).
    Priority 2: partial full_name match (case-insensitive) — only if no username hit.
    Returns None if not found. Raises ValueError if ambiguous.
    """
    name_lower = name.lstrip("@").lower()

    # Priority 1: exact username match
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            "SELECT chat_id, full_name FROM user_registry WHERE lower(username) = ?",
            (name_lower,),
        ).fetchall()
    if len(rows) == 1:
        return rows[0][0], rows[0][1]
    if len(rows) > 1:
        names = ", ".join(r[1] or str(r[0]) for r in rows)
        raise ValueError(f"ambiguous: matches {names}")

    # Priority 2: partial full_name match (only if no username hit)
    like_safe = name_lower.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            "SELECT chat_id, full_name FROM user_registry WHERE lower(full_name) LIKE ? ESCAPE '\\'",
            (f"%{like_safe}%",),
        ).fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        names = ", ".join(r[1] or str(r[0]) for r in rows)
        raise ValueError(f"ambiguous: matches {names}")
    return rows[0][0], rows[0][1]
