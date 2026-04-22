import sqlite3
from pathlib import Path
import pytest

from agents.main.shared_context import init_shared_context_tables, db_upsert_user, db_resolve_user


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_shared_context_tables(db_path)
    return db_path


def test_tables_created(db):
    with sqlite3.connect(db) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "user_registry" in tables
    assert "shared_context" in tables


def test_user_registry_schema(db):
    with sqlite3.connect(db) as con:
        cols = {
            row[1]
            for row in con.execute("PRAGMA table_info(user_registry)").fetchall()
        }
    assert cols == {"chat_id", "user_id", "username", "full_name", "last_seen"}


def test_shared_context_schema(db):
    with sqlite3.connect(db) as con:
        cols = {
            row[1]
            for row in con.execute("PRAGMA table_info(shared_context)").fetchall()
        }
    assert cols == {
        "id", "from_chat_id", "to_chat_id", "content",
        "label", "shared_at", "acknowledged", "revoked",
    }


def test_upsert_user_inserts(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name="Jay Fabor")
    with sqlite3.connect(db) as con:
        row = con.execute("SELECT * FROM user_registry WHERE chat_id=100").fetchone()
    assert row is not None
    assert row[2] == "jay"
    assert row[3] == "Jay Fabor"


def test_upsert_user_updates_on_conflict(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name="Jay Fabor")
    db_upsert_user(db, chat_id=100, user_id=1, username="jay2", full_name="Jay Fabor Updated")
    with sqlite3.connect(db) as con:
        rows = con.execute("SELECT * FROM user_registry WHERE chat_id=100").fetchall()
    assert len(rows) == 1
    assert rows[0][2] == "jay2"


def test_resolve_user_by_username(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name="Jay Fabor")
    result = db_resolve_user(db, "jay")
    assert result == (100, "Jay Fabor")


def test_resolve_user_by_full_name(db):
    db_upsert_user(db, chat_id=100, user_id=1, username=None, full_name="Jay Fabor")
    result = db_resolve_user(db, "Jay")
    assert result == (100, "Jay Fabor")


def test_resolve_user_case_insensitive(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="JAY", full_name="Jay Fabor")
    result = db_resolve_user(db, "jay")
    assert result == (100, "Jay Fabor")


def test_resolve_user_not_found(db):
    result = db_resolve_user(db, "nobody")
    assert result is None


def test_resolve_user_ambiguous_raises(db):
    db_upsert_user(db, chat_id=100, user_id=1, username=None, full_name="Jay One")
    db_upsert_user(db, chat_id=101, user_id=2, username=None, full_name="Jay Two")
    with pytest.raises(ValueError, match="ambiguous"):
        db_resolve_user(db, "Jay")


def test_resolve_user_null_full_name(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name=None)
    result = db_resolve_user(db, "jay")
    assert result == (100, None)
