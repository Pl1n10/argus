"""The actual monitoring rules: state computation, alert transitions, anomaly.

Pure functions over plain dicts + an injected `now`. No DB, no channels — the
service layer (monitor.py) wires these to storage and notifications. This is
where the three product questions live:

  1. did it run?      -> dead-man's switch (compute_state -> 'late')
  2. did it succeed?  -> last ping status  (compute_state -> 'failed')
  3. does it look sane?-> size_anomaly
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from argus.clock import from_iso
from argus.scheduling import next_expected

# States that represent something a human should look at.
ALERTING_STATES = ("late", "failed")


def compute_state(
    *,
    last_ping_at: str | None,
    last_status: str | None,
    schedule_kind: str,
    schedule_expr: str,
    grace_seconds: int,
    now: datetime,
) -> str:
    """Derive a job's current state.

    - never pinged            -> 'new' (the switch only arms after the first
      ping, like Healthchecks; an unconfigured job shouldn't page you)
    - last ping failed        -> 'failed' (takes precedence: a failure is
      actionable regardless of timing)
    - silent past deadline    -> 'late'  (schedule + grace exceeded)
    - otherwise               -> 'up'
    """
    if last_ping_at is None:
        return "new"
    if last_status == "fail":
        return "failed"
    last = from_iso(last_ping_at)
    deadline = next_expected(schedule_kind, schedule_expr, last) + timedelta(seconds=grace_seconds)
    return "late" if now > deadline else "up"


@dataclass
class Alert:
    job_name: str
    state: str          # 'late' | 'failed' | 'up' (up = recovery)
    detail: str = ""
    recovery: bool = False


def evaluate(job: dict, now: datetime) -> tuple[str, str | None, Alert | None]:
    """Compute (new_state, new_alerted_state, alert_to_send) for a job.

    Alerting is edge-triggered for de-duplication: we fire once when a job
    enters late/failed, and once more on recovery, never on every sweep.
    `job` must carry: name, state, alerted_state, paused, last_ping_at,
    last_status, schedule_kind, schedule_expr, grace_seconds.
    """
    if job["paused"]:
        return job["state"], job["alerted_state"], None

    state = compute_state(
        last_ping_at=job["last_ping_at"],
        last_status=job.get("last_status"),
        schedule_kind=job["schedule_kind"],
        schedule_expr=job["schedule_expr"],
        grace_seconds=job["grace_seconds"],
        now=now,
    )
    alerted = job["alerted_state"]

    if state in ALERTING_STATES and alerted != state:
        return state, state, Alert(job["name"], state, detail=_detail(job, state))
    if state == "up" and alerted is not None:
        return state, None, Alert(job["name"], "up", detail="recovered", recovery=True)
    return state, alerted, None


def _detail(job: dict, state: str) -> str:
    if state == "failed":
        ec = job.get("last_exit_code")
        return f"last run failed (exit {ec})" if ec is not None else "last run failed"
    if state == "late":
        return f"no report since {job['last_ping_at']} (schedule + grace exceeded)"
    return ""


def _deviation_anomaly(
    history: list[float],
    latest: float | None,
    threshold_pct: float,
    min_history: int,
) -> bool:
    """True when `latest` deviates more than threshold_pct from the rolling
    median of `history` (D-008: simple rule, no ML).

    `history` EXCLUDES the latest value. Returns False until we have at least
    `min_history` prior points — anomaly detection on two points is noise.
    A zero against a non-zero history always trips (the empty-dump / instant-run
    case the rule exists for).
    """
    if latest is None or len(history) < min_history:
        return False
    base = median(history)
    if base == 0:
        return latest != 0
    return abs(latest - base) / base * 100.0 > threshold_pct


def size_anomaly(
    sizes: list[int],
    latest: int | None,
    *,
    threshold_pct: float = 30.0,
    min_history: int = 3,
) -> bool:
    """Size deviation warning: empty dump, runaway growth, truncated archive."""
    return _deviation_anomaly(sizes, latest, threshold_pct, min_history)


def duration_anomaly(
    durations: list[float],
    latest: float | None,
    *,
    threshold_pct: float = 30.0,
    min_history: int = 3,
) -> bool:
    """Duration deviation warning (D-008: same rule as size, warn-only): a run
    that suddenly takes far longer or returns instantly is worth a look."""
    return _deviation_anomaly(durations, latest, threshold_pct, min_history)
