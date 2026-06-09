"""Time helpers. Everything is UTC and timezone-aware.

Centralised so tests can reason about a single notion of "now" and so the ISO
format on the wire is consistent. SQLite stores these as strings; we never do
date math in SQL (see schema.sql).
"""
from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current time, timezone-aware UTC."""
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    """Serialise a datetime to an ISO-8601 UTC string."""
    return dt.astimezone(UTC).isoformat()


def from_iso(s: str) -> datetime:
    """Parse an ISO-8601 string back to a timezone-aware UTC datetime.

    Accepts both the Python `+00:00` form and a trailing `Z` (3.12's
    fromisoformat handles `Z`, but the SQL `created_at` default emits `Z`,
    so be explicit and tolerant).
    """
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
