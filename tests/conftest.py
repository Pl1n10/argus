"""Shared test fixtures.

Everything is in-memory and clock-injectable: no real DB file, no network, no
APScheduler thread. Alert channels are a recording fake (global rule: never hit
ntfy/Telegram in tests).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argus.db import Store
from argus.server import create_app

SCHEMA = (Path(__file__).resolve().parent.parent / "argus" / "schema.sql").read_text()


def at(y, mo, d, h=0, mi=0, s=0) -> datetime:
    """Convenience UTC datetime builder for deterministic tests."""
    return datetime(y, mo, d, h, mi, s, tzinfo=UTC)


class RecordingChannel:
    """A fake alert channel that just remembers what it was asked to send."""

    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, subject: str, body: str) -> None:
        self.sent.append((subject, body))


@pytest.fixture
def store() -> Store:
    s = Store(db_path=":memory:", schema_sql=SCHEMA)
    yield s
    s.close()


@pytest.fixture
def channel() -> RecordingChannel:
    return RecordingChannel()


@pytest.fixture
def client(store, channel) -> TestClient:
    app = create_app(store, [channel], base_url="http://test.local")
    return TestClient(app)


@pytest.fixture
def auth_client(store, channel) -> TestClient:
    app = create_app(store, [channel], base_url="http://test.local", admin_token="s3cret")
    return TestClient(app)
