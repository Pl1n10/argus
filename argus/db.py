"""SQLite persistence. One Store wraps one connection, serialised by a lock.

check_same_thread=False because FastAPI runs sync endpoints in a threadpool and
APScheduler sweeps from its own thread; the RLock serialises every access, and
SQLite is a single-writer anyway at this (trivial) write volume. WAL keeps the
sweep's reads from blocking an ingest write. Pattern lifted from pocket-dnd D4.
"""
from __future__ import annotations

import secrets
import sqlite3
import threading
from datetime import datetime

from argus.clock import to_iso, utcnow
from argus.ingest import PingData

# Columns selected for a job, plus the latest ping's status/exit_code/bytes
# denormalised in — checks.evaluate needs "did the last run fail?" without a
# second round trip.
_JOB_SELECT = """
    SELECT j.*,
           p.status    AS last_status,
           p.exit_code AS last_exit_code,
           p.bytes     AS last_bytes
    FROM jobs j
    LEFT JOIN pings p ON p.id = (
        SELECT id FROM pings WHERE job_id = j.id
        ORDER BY received_at DESC, id DESC LIMIT 1
    )
"""


class JobNotFound(LookupError):
    """No job with that id or token."""


class Store:
    def __init__(self, db_path: str, schema_sql: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # WAL is a no-op (returns 'memory') for :memory: DBs — harmless.
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(schema_sql)
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ─────────────────────────────── jobs ───────────────────────────────

    def create_job(self, *, name: str, schedule_kind: str, schedule_expr: str,
                   grace_seconds: int) -> dict:
        name = (name or "").strip()
        if not name:
            raise ValueError("job name is required")
        token = secrets.token_urlsafe(24)
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO jobs (token, name, schedule_kind, schedule_expr, grace_seconds) "
                "VALUES (?, ?, ?, ?, ?)",
                (token, name, schedule_kind, str(schedule_expr), grace_seconds),
            )
            self._conn.commit()
            return self._get_by_id_locked(cur.lastrowid)

    def list_jobs(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(_JOB_SELECT + " ORDER BY j.name COLLATE NOCASE").fetchall()
            return [dict(r) for r in rows]

    def get_job(self, job_id: int) -> dict:
        with self._lock:
            return self._get_by_id_locked(job_id)

    def get_job_by_token(self, token: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                _JOB_SELECT + " WHERE j.token = ?", (token,)).fetchone()
            return dict(row) if row else None

    def delete_job(self, job_id: int) -> None:
        with self._lock:
            cur = self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            self._conn.commit()
            if cur.rowcount == 0:
                raise JobNotFound(job_id)

    def set_paused(self, job_id: int, paused: bool) -> dict:
        with self._lock:
            self._conn.execute("UPDATE jobs SET paused = ? WHERE id = ?",
                               (1 if paused else 0, job_id))
            self._conn.commit()
            return self._get_by_id_locked(job_id)

    def _get_by_id_locked(self, job_id: int) -> dict:
        row = self._conn.execute(_JOB_SELECT + " WHERE j.id = ?", (job_id,)).fetchone()
        if row is None:
            raise JobNotFound(job_id)
        return dict(row)

    # ─────────────────────────────── pings ──────────────────────────────

    def record_ping(self, job_id: int, ping: PingData, *, now: datetime | None = None) -> dict:
        """Insert a ping and stamp the job's last_ping_at. Returns the fresh job
        row (state is updated separately by the monitor's evaluate step)."""
        received = to_iso(now or utcnow())
        with self._lock:
            self._get_by_id_locked(job_id)  # raises JobNotFound if gone
            self._conn.execute(
                "INSERT INTO pings (job_id, received_at, flavor, status, exit_code, "
                "bytes, duration_s, log_tail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, received, ping.flavor, ping.status, ping.exit_code,
                 ping.bytes, ping.duration_s, ping.log_tail),
            )
            self._conn.execute("UPDATE jobs SET last_ping_at = ? WHERE id = ?",
                               (received, job_id))
            self._conn.commit()
            return self._get_by_id_locked(job_id)

    def recent_sizes(self, job_id: int, limit: int = 10) -> list[int]:
        """Sizes of the most recent successful pings that reported bytes,
        oldest→newest. Drives the anomaly check and the sparkline."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT bytes FROM pings WHERE job_id = ? AND status = 'success' "
                "AND bytes IS NOT NULL ORDER BY received_at DESC, id DESC LIMIT ?",
                (job_id, limit),
            ).fetchall()
        return [r["bytes"] for r in reversed(rows)]

    # ─────────────────────────── state / alerts ─────────────────────────

    def update_evaluation(self, job_id: int, state: str, alerted_state: str | None) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE jobs SET state = ?, alerted_state = ? WHERE id = ?",
                (state, alerted_state, job_id))
            self._conn.commit()
