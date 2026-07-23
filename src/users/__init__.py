"""
User tracking and activity log for AViD Journal.

SQLite-backed: stores registered users and every action they take.
Used for: onboarding emails, usage stats, knowing who published what.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent / "users.db"

logger = logging.getLogger(__name__)


def _conn() -> sqlite3.Connection:
    """Get a connection to the SQLite database (auto-creates tables)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            google_id    TEXT PRIMARY KEY,
            email        TEXT NOT NULL,
            name         TEXT NOT NULL,
            picture      TEXT DEFAULT '',
            api_key_mode TEXT DEFAULT 'server',  -- 'server' or 'user'
            created_at   TEXT NOT NULL,
            last_login   TEXT NOT NULL,
            login_count  INTEGER DEFAULT 1,
            papers_submitted INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS activity (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id    TEXT NOT NULL,
            action       TEXT NOT NULL,   -- 'login', 'analyze', 'publish', 'logout'
            details      TEXT DEFAULT '{}',
            created_at   TEXT NOT NULL,
            FOREIGN KEY (google_id) REFERENCES users(google_id)
        );

        CREATE INDEX IF NOT EXISTS idx_activity_google_id ON activity(google_id);
        CREATE INDEX IF NOT EXISTS idx_activity_action ON activity(action);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """)


# ── User CRUD ──────────────────────────────────────────────────────────────


def upsert_user(
    google_id: str,
    email: str,
    name: str,
    picture: str = "",
) -> dict:
    """Insert or update a user on login. Returns the user record."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()

    existing = conn.execute(
        "SELECT * FROM users WHERE google_id = ?", (google_id,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE users SET email=?, name=?, picture=?, last_login=?,
               login_count = login_count + 1 WHERE google_id=?""",
            (email, name, picture, now, google_id),
        )
    else:
        conn.execute(
            """INSERT INTO users (google_id, email, name, picture, created_at, last_login)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (google_id, email, name, picture, now, now),
        )

    conn.commit()
    return dict(conn.execute(
        "SELECT * FROM users WHERE google_id=?", (google_id,)
    ).fetchone())


def get_user(google_id: str) -> Optional[dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE google_id=?", (google_id,)).fetchone()
    return dict(row) if row else None


def set_api_key_mode(google_id: str, mode: str) -> None:
    """Update whether the user uses server key or their own key."""
    conn = _conn()
    conn.execute(
        "UPDATE users SET api_key_mode=? WHERE google_id=?",
        (mode, google_id),
    )
    conn.commit()


def increment_papers(google_id: str) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE users SET papers_submitted = papers_submitted + 1 WHERE google_id=?",
        (google_id,),
    )
    conn.commit()


# ── Activity log ───────────────────────────────────────────────────────────


def log_action(google_id: str, action: str, details: Optional[dict] = None) -> None:
    """Record a user action in the activity log."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    conn.execute(
        "INSERT INTO activity (google_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (google_id, action, json.dumps(details or {}, ensure_ascii=False), now),
    )
    conn.commit()


def get_activity(google_id: str, limit: int = 50) -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM activity WHERE google_id=? ORDER BY created_at DESC LIMIT ?",
        (google_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def stats() -> dict:
    """Return global stats for the journal."""
    conn = _conn()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_papers = conn.execute(
        "SELECT COALESCE(SUM(papers_submitted), 0) FROM users"
    ).fetchone()[0]
    total_analyses = conn.execute(
        "SELECT COUNT(*) FROM activity WHERE action='analyze'"
    ).fetchone()[0]
    return {
        "users": total_users,
        "papers_submitted": total_papers,
        "analyses_run": total_analyses,
    }
