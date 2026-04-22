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


def db_share_context(
    db_path: Path,
    from_chat_id: int,
    to_chat_id: int,
    content: str,
    label: Optional[str] = None,
) -> int:
    """Insert a shared context item. Returns the new row id."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """INSERT INTO shared_context (from_chat_id, to_chat_id, content, label)
               VALUES (?, ?, ?, ?)""",
            (from_chat_id, to_chat_id, content, label),
        )
        return cur.lastrowid


def db_get_unacknowledged_shared(db_path: Path, chat_id: int) -> list[dict]:
    """Return unacknowledged, non-revoked shared items for chat_id."""
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """SELECT sc.id, sc.from_chat_id, sc.content, sc.shared_at,
                      COALESCE(ur.full_name, cast(sc.from_chat_id as text)) as from_name
               FROM shared_context sc
               LEFT JOIN user_registry ur ON ur.chat_id = sc.from_chat_id
               WHERE sc.to_chat_id = ? AND sc.acknowledged = 0 AND sc.revoked = 0
               ORDER BY sc.shared_at ASC""",
            (chat_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def db_mark_acknowledged(db_path: Path, chat_id: int) -> None:
    """Mark all unacknowledged shared items for chat_id as read."""
    with sqlite3.connect(db_path) as con:
        con.execute(
            "UPDATE shared_context SET acknowledged=1 WHERE to_chat_id=? AND acknowledged=0",
            (chat_id,),
        )


def db_revoke_shared(
    db_path: Path, from_chat_id: int, to_chat_id: int, content_hint: str
) -> list[int]:
    """
    Soft-delete shared items from from_chat_id to to_chat_id matching content_hint.
    Matches by label (exact) or content substring. Returns list of revoked row ids.
    """
    hint_lower = content_hint.lower()
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """SELECT id FROM shared_context
               WHERE from_chat_id=? AND to_chat_id=? AND revoked=0
                 AND (lower(label)=? OR lower(content) LIKE ?)""",
            (from_chat_id, to_chat_id, hint_lower, f"%{hint_lower}%"),
        ).fetchall()
        ids = [r[0] for r in rows]
        if ids:
            con.execute(
                f"UPDATE shared_context SET revoked=1 WHERE id IN ({','.join('?' * len(ids))})",
                ids,
            )
    return ids


def db_list_shared(db_path: Path, to_chat_id: int) -> list[dict]:
    """Return all non-revoked shared items for chat_id, newest first."""
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """SELECT sc.id, sc.from_chat_id, sc.content, sc.shared_at, sc.label,
                      COALESCE(ur.full_name, cast(sc.from_chat_id as text)) as from_name
               FROM shared_context sc
               LEFT JOIN user_registry ur ON ur.chat_id = sc.from_chat_id
               WHERE sc.to_chat_id=? AND sc.revoked=0
               ORDER BY sc.from_chat_id, sc.shared_at DESC""",
            (to_chat_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def format_shared_note(items: list[dict]) -> str:
    """Format a list of shared items as a system note for Claude injection."""
    if not items:
        return ""
    lines = []
    for item in items:
        date_str = item["shared_at"][:10]
        lines.append(f"From {item['from_name']} ({date_str}): {item['content']}")
    return "\n".join(lines)
