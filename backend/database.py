"""
SentinelFlow SQLite Database Layer.
Provides schema initialization, seed data management, and transactional event logging.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from config import DATABASE_PATH
from src.event_schema import SessionEvent


def get_db_connection(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Create a thread-safe connection to SQLite database."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DATABASE_PATH) -> None:
    """Initialize database tables and seed default fictional users."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # Users Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        account_number TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 12450.75,
        created_at TEXT NOT NULL
    )
    """)

    # Sessions Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        is_verified INTEGER NOT NULL DEFAULT 0,
        device_familiarity TEXT NOT NULL DEFAULT 'familiar',
        location_context TEXT NOT NULL DEFAULT 'home',
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Events Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        timestamp_utc TEXT NOT NULL,
        success INTEGER NOT NULL DEFAULT 1,
        device_familiarity TEXT NOT NULL,
        location_context TEXT NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    )
    """)

    # Verification Challenges Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS verifications (
        challenge_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    )
    """)

    # Seed demo users if empty
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    if cur.fetchone()["cnt"] == 0:
        now_iso = datetime.now(timezone.utc).isoformat()
        demo_users = [
            ("user-alex-01", "alex_demo", "Alex Mercer", "ACC-7890-4123", 14850.50, now_iso),
            ("user-jordan-02", "jordan_demo", "Jordan Blake", "ACC-4521-8890", 8230.15, now_iso),
            ("user-sam-03", "sam_demo", "Sam Morgan", "ACC-1102-6745", 25400.00, now_iso),
        ]
        cur.executemany(
            "INSERT INTO users (user_id, username, full_name, account_number, balance, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            demo_users,
        )

    conn.commit()
    conn.close()


def insert_event(event: SessionEvent, db_path: Path = DATABASE_PATH) -> None:
    """Persist a single validated SessionEvent into the events table."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events (
            event_id, session_id, user_id, event_type, timestamp_utc,
            success, device_familiarity, location_context, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.event_id,
            event.session_id,
            event.user_id,
            event.event_type,
            event.timestamp_utc,
            1 if event.success else 0,
            event.device_familiarity,
            event.location_context,
            json.dumps(event.metadata),
        ),
    )
    conn.commit()
    conn.close()


def get_session_events(session_id: str, db_path: Path = DATABASE_PATH) -> List[SessionEvent]:
    """Retrieve all chronologically ordered events for a session."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT event_id, session_id, user_id, event_type, timestamp_utc,
               success, device_familiarity, location_context, metadata_json
        FROM events
        WHERE session_id = ?
        ORDER BY timestamp_utc ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()

    events = []
    for r in rows:
        meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
        events.append(
            SessionEvent(
                event_id=r["event_id"],
                session_id=r["session_id"],
                user_id=r["user_id"],
                event_type=r["event_type"],
                timestamp_utc=r["timestamp_utc"],
                success=bool(r["success"]),
                device_familiarity=r["device_familiarity"],
                location_context=r["location_context"],
                metadata=meta,
            )
        )
    return events


def set_session_verified(session_id: str, is_verified: bool = True, db_path: Path = DATABASE_PATH) -> None:
    """Update verification status for a session."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET is_verified = ? WHERE session_id = ?",
        (1 if is_verified else 0, session_id),
    )
    conn.commit()
    conn.close()


def get_session_info(session_id: str, db_path: Path = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve session record with verification flag."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.session_id, s.user_id, s.is_verified, s.device_familiarity, s.location_context, s.created_at,
               u.username, u.full_name, u.account_number, u.balance
        FROM sessions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.session_id = ?
        """,
        (session_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)
