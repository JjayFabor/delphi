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
