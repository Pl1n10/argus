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
from argus.checks import Alert, duration_anomaly, evaluate, size_anomaly
from argus.clock import utcnow
from argus.db import Store


def evaluate_job(store: Store, job: dict, channels: list[Channel],
                 now: datetime | None = None) -> Alert | None:
    """Evaluate a single job dict, persist the new state, send any alert.

    Returns the state-transition alert (late/failed/recovery) if one fired. The
    warn-level anomaly alert is a separate axis and is sent independently — a
    job can be 'up' yet have an anomalous backup size, and the product thesis is
    that nobody watches the dashboard, so the anomaly must page too (not just
    render). Both are edge-triggered for de-duplication.
    """
    now = now or utcnow()
    state, alerted_state, alert = evaluate(job, now)
    if state != job["state"] or alerted_state != job["alerted_state"]:
        store.update_evaluation(job["id"], state, alerted_state)
    if alert is not None:
        notify(channels, alert)

    anomaly_alert = _evaluate_anomaly(store, job)
    if anomaly_alert is not None:
        notify(channels, anomaly_alert)

    return alert


def _evaluate_anomaly(store: Store, job: dict) -> Alert | None:
    """Check the latest backup's size/duration against its history and emit a
    warn alert on the transition into anomalous, clearing the flag on the way
    back to normal. No alert spam: one page per anomaly episode."""
    sizes = store.recent_sizes(job["id"], 10)
    durations = store.recent_durations(job["id"], 10)
    size_bad = size_anomaly(sizes[:-1], sizes[-1]) if sizes else False
    dur_bad = duration_anomaly(durations[:-1], durations[-1]) if durations else False
    tripped = size_bad or dur_bad
    already = bool(job["anomaly_alerted"])

    if tripped and not already:
        store.set_anomaly_alerted(job["id"], True)
        parts = []
        if size_bad:
            parts.append(f"size {sizes[-1]} B")
        if dur_bad:
            parts.append(f"duration {durations[-1]}s")
        return Alert(job["name"], "warn",
                     detail="anomaly: " + ", ".join(parts) + " deviates from history")
    if not tripped and already:
        store.set_anomaly_alerted(job["id"], False)
    return None


def sweep(store: Store, channels: list[Channel], now: datetime | None = None) -> list[Alert]:
    """Evaluate all jobs. Returns the alerts fired (handy for tests/logging)."""
    now = now or utcnow()
    fired: list[Alert] = []
    for job in store.list_jobs():
        alert = evaluate_job(store, job, channels, now)
        if alert is not None:
            fired.append(alert)
    return fired
