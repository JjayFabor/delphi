"""
agents/main/scheduler.py — Scheduled task persistence and schedule parsing.

Tasks are stored in SQLite. The JobQueue integration lives in agent.py.
"""
import logging
import re
import sqlite3
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

logger = logging.getLogger("scheduler")


# ── Schedule parser ────────────────────────────────────────────────────────────

def _parse_clock(s: str) -> dtime:
    """Parse a clock string like '9am', '14:30', '9:00 pm' into a datetime.time."""
    s = s.strip().lower()
    m = re.match(r"(\d{1,2}):(\d{2})\s*(am|pm)?", s)
    if m:
        h, mi, period = int(m.group(1)), int(m.group(2)), m.group(3)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return dtime(h % 24, mi)
    m = re.match(r"(\d{1,2})\s*(am|pm)", s)
    if m:
        h, period = int(m.group(1)), m.group(2)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return dtime(h % 24, 0)
    raise ValueError(f"Cannot parse time: {s!r}")


def parse_schedule(text: str) -> dict:
    """
    Parse a natural-language schedule string.

    Returns one of:
      {"type": "interval", "seconds": N}
      {"type": "daily",    "time": "HH:MM"}

    Raises ValueError if the string cannot be parsed.
    """
    t = text.strip().lower()

    # "every N minutes/hours"
    m = re.match(r"every\s+(\d+)\s+(minute|minutes|min|hour|hours|hr|hrs)", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        secs = n * 60 if "min" in unit else n * 3600
        return {"type": "interval", "seconds": secs}

    # "every day at HH:MM" / "daily at 9am"
    m = re.search(r"(?:every day|daily)\s+at\s+(.+)", t)
    if m:
        clock = _parse_clock(m.group(1))
        return {"type": "daily", "time": f"{clock.hour:02d}:{clock.minute:02d}"}

    # Named times
    if "morning" in t:
        return {"type": "daily", "time": "08:00"}
    if "noon" in t:
        return {"type": "daily", "time": "12:00"}
    if "evening" in t:
        return {"type": "daily", "time": "18:00"}
    if "night" in t or "midnight" in t:
        return {"type": "daily", "time": "00:00"}

    raise ValueError(
        f"Cannot parse schedule: {text!r}. "
        "Try: 'every 30 minutes', 'every 2 hours', 'every day at 9am', 'daily at 14:30'"
    )


def parse_once(text: str) -> datetime:
    """
    Parse a one-shot schedule string and return the absolute datetime to fire.

    Accepts:
      "in N minutes" / "in N hours" / "in N seconds"
      "at HH:MM" / "at 9am" / "at 2:30pm"
      "tomorrow at 9am"
    """
    t = text.strip().lower()
    now = datetime.now()

    # "in N minutes/hours/seconds"
    m = re.match(r"in\s+(\d+)\s+(second|seconds|sec|minute|minutes|min|hour|hours|hr|hrs)", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if "sec" in unit:
            delta = timedelta(seconds=n)
        elif "min" in unit:
            delta = timedelta(minutes=n)
        else:
            delta = timedelta(hours=n)
        return now + delta

    # "tomorrow at <time>"
    m = re.search(r"tomorrow\s+at\s+(.+)", t)
    if m:
        clock = _parse_clock(m.group(1))
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, clock)

    # "at <time>" (today; if already past, fire tomorrow)
    m = re.search(r"\bat\s+(.+)", t)
    if m:
        clock = _parse_clock(m.group(1))
        candidate = datetime.combine(now.date(), clock)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    raise ValueError(
        f"Cannot parse one-shot schedule: {text!r}. "
        "Try: 'in 30 minutes', 'in 2 hours', 'at 9am', 'at 14:30', 'tomorrow at 9am'"
    )


# ── DB helpers ─────────────────────────────────────────────────────────────────

def init_scheduler_table(db_path: Path) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id        INTEGER NOT NULL,
                task_prompt    TEXT NOT NULL,
                schedule_str   TEXT NOT NULL,
                schedule_type  TEXT NOT NULL,
                schedule_value TEXT NOT NULL,
                enabled        INTEGER NOT NULL DEFAULT 1,
                created_at     TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


def db_add_task(db_path: Path, chat_id: int, task_prompt: str, schedule_str: str) -> int:
    """Parse schedule, persist task, and return new task ID."""
    parsed = parse_schedule(schedule_str)
    stype = parsed["type"]
    svalue = str(parsed.get("seconds") or parsed.get("time", ""))
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """INSERT INTO scheduled_tasks
               (chat_id, task_prompt, schedule_str, schedule_type, schedule_value)
               VALUES (?, ?, ?, ?, ?)""",
            (chat_id, task_prompt, schedule_str, stype, svalue),
        )
        return cur.lastrowid


def db_remove_task(db_path: Path, task_id: int, chat_id: int) -> bool:
    """Delete a task. Returns True if a row was deleted."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "DELETE FROM scheduled_tasks WHERE id = ? AND chat_id = ?",
            (task_id, chat_id),
        )
        return cur.rowcount > 0


def db_list_tasks(db_path: Path, chat_id: int) -> list[dict]:
    """Return all tasks for a chat, enabled or not."""
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            "SELECT id, task_prompt, schedule_str, enabled FROM scheduled_tasks "
            "WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
    return [
        {"id": r[0], "task_prompt": r[1], "schedule_str": r[2], "enabled": bool(r[3])}
        for r in rows
    ]


def db_all_enabled_tasks(db_path: Path) -> list[dict]:
    """Return all enabled tasks (used at startup to restore the JobQueue)."""
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            "SELECT id, chat_id, task_prompt, schedule_type, schedule_value "
            "FROM scheduled_tasks WHERE enabled = 1"
        ).fetchall()
    return [
        {
            "id": r[0],
            "chat_id": r[1],
            "task_prompt": r[2],
            "schedule_type": r[3],
            "schedule_value": r[4],
        }
        for r in rows
    ]
