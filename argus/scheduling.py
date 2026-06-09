"""Schedule parsing and "when should this job next have run?" math.

Two schedule kinds (MVP):
  - interval: `schedule_expr` is a whole number of SECONDS between runs.
  - cron:     `schedule_expr` is a standard 5-field cron expression.

Kept pure (no DB, no clock-of-record) so the dead-man's-switch logic in
checks.py is trivially testable with an injected `now`.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from croniter import croniter


class ScheduleError(ValueError):
    """The schedule kind/expression is malformed."""


def interval_seconds(expr: str) -> int:
    """Parse an interval expression (a count of seconds) into an int > 0."""
    try:
        secs = int(str(expr).strip())
    except (TypeError, ValueError) as e:
        raise ScheduleError(
            f"interval must be an integer number of seconds, got {expr!r}") from e
    if secs <= 0:
        raise ScheduleError("interval seconds must be positive")
    return secs


def validate(kind: str, expr: str) -> None:
    """Raise ScheduleError unless (kind, expr) is a schedule we can evaluate."""
    if kind == "interval":
        interval_seconds(expr)  # raises if bad
    elif kind == "cron":
        if not croniter.is_valid(expr):
            raise ScheduleError(f"invalid cron expression: {expr!r}")
    else:
        raise ScheduleError(f"unknown schedule kind: {kind!r}")


def next_expected(kind: str, expr: str, after: datetime) -> datetime:
    """The first moment a run is expected strictly AFTER `after`.

    For an interval job this is `after + interval`. For a cron job it is the
    next cron firing after `after`. The dead-man's switch adds the grace period
    to this and alerts once `now` passes it.
    """
    if kind == "interval":
        return after + timedelta(seconds=interval_seconds(expr))
    if kind == "cron":
        return croniter(expr, after).get_next(datetime)
    raise ScheduleError(f"unknown schedule kind: {kind!r}")
