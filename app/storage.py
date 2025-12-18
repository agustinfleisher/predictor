"""
SQLite-backed persistence for users and jobs.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from .config import Settings, resolve_db_path


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def init_db(settings: Settings) -> None:
    db_path = resolve_db_path(settings)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_conn(settings: Settings):
    db_path = resolve_db_path(settings)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_user(settings: Settings, email: str, password_hash: str) -> int:
    with get_conn(settings) as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, password_hash, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid


def get_user_by_email(settings: Settings, email: str) -> Optional[Dict[str, Any]]:
    with get_conn(settings) as conn:
        cur = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_id(settings: Settings, user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn(settings) as conn:
        cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_job(settings: Settings, job_id: str, user_id: int, request_json: dict) -> None:
    payload = json.dumps(request_json)
    now = _now_iso()
    with get_conn(settings) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, user_id, status, request_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, user_id, "running", payload, now, now),
        )
        conn.commit()


def update_job(
    settings: Settings,
    job_id: str,
    status: str,
    result_json: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    now = _now_iso()
    result_payload = json.dumps(result_json) if result_json is not None else None
    with get_conn(settings) as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, result_json = ?, error = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, result_payload, error, now, job_id),
        )
        conn.commit()


def get_job(settings: Settings, job_id: str) -> Optional[Dict[str, Any]]:
    with get_conn(settings) as conn:
        cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        rec = dict(row)
        if rec.get("request_json"):
            rec["request_json"] = json.loads(rec["request_json"])
        if rec.get("result_json"):
            rec["result_json"] = json.loads(rec["result_json"])
        return rec


def list_jobs(settings: Settings, user_id: int, limit: int = 20) -> Iterable[Dict[str, Any]]:
    with get_conn(settings) as conn:
        cur = conn.execute(
            """
            SELECT id, status, created_at, updated_at
            FROM jobs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        for row in cur.fetchall():
            yield dict(row)
