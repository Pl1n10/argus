"""Service layer: wire the pure rules (checks.py) to storage + channels.

Two entry points, both idempotent and clock-injectable:
  - evaluate_job: re-derive one job's state, persist it, fire any transition
    alert. Called right after an ingest (a ping can flip failed/up).
  - sweep: evaluate every job. Called on a timer by APScheduler — this is what
    turns silence into a 'late' alert (the dead-man's switch).
"""
from __future__ import annotations

from datetime import datetime

from argus.alerts import Channel, notify
from argus.checks import Alert, evaluate
from argus.clock import utcnow
from argus.db import Store


def evaluate_job(store: Store, job: dict, channels: list[Channel],
                 now: datetime | None = None) -> Alert | None:
    """Evaluate a single job dict, persist the new state, send any alert."""
    now = now or utcnow()
    state, alerted_state, alert = evaluate(job, now)
    if state != job["state"] or alerted_state != job["alerted_state"]:
        store.update_evaluation(job["id"], state, alerted_state)
    if alert is not None:
        notify(channels, alert)
    return alert


def sweep(store: Store, channels: list[Channel], now: datetime | None = None) -> list[Alert]:
    """Evaluate all jobs. Returns the alerts fired (handy for tests/logging)."""
    now = now or utcnow()
    fired: list[Alert] = []
    for job in store.list_jobs():
        alert = evaluate_job(store, job, channels, now)
        if alert is not None:
            fired.append(alert)
    return fired
