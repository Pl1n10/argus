from argus.checks import (
    Alert,
    compute_state,
    duration_anomaly,
    evaluate,
    size_anomaly,
)
from tests.conftest import at


def _job(**over):
    base = {
        "id": 1, "name": "nightly", "state": "new", "alerted_state": None,
        "paused": 0, "last_ping_at": None, "last_status": None,
        "schedule_kind": "interval", "schedule_expr": "3600", "grace_seconds": 600,
    }
    base.update(over)
    return base


class TestComputeState:
    def test_never_pinged_is_new(self):
        assert compute_state(last_ping_at=None, last_status=None,
                             schedule_kind="interval", schedule_expr="3600",
                             grace_seconds=600, now=at(2026, 6, 9, 12)) == "new"

    def test_recent_success_is_up(self):
        s = compute_state(last_ping_at="2026-06-09T12:00:00+00:00", last_status="success",
                         schedule_kind="interval", schedule_expr="3600",
                         grace_seconds=600, now=at(2026, 6, 9, 12, 30))
        assert s == "up"

    def test_within_grace_is_up(self):
        # next expected 13:00, grace 600s -> deadline 13:10; at 13:05 still up
        s = compute_state(last_ping_at="2026-06-09T12:00:00+00:00", last_status="success",
                         schedule_kind="interval", schedule_expr="3600",
                         grace_seconds=600, now=at(2026, 6, 9, 13, 5))
        assert s == "up"

    def test_past_grace_is_late(self):
        s = compute_state(last_ping_at="2026-06-09T12:00:00+00:00", last_status="success",
                         schedule_kind="interval", schedule_expr="3600",
                         grace_seconds=600, now=at(2026, 6, 9, 13, 11))
        assert s == "late"

    def test_failed_takes_precedence(self):
        s = compute_state(last_ping_at="2026-06-09T12:00:00+00:00", last_status="fail",
                         schedule_kind="interval", schedule_expr="3600",
                         grace_seconds=600, now=at(2026, 6, 9, 12, 1))
        assert s == "failed"


class TestEvaluate:
    def test_new_job_no_alert(self):
        state, alerted, alert = evaluate(_job(), at(2026, 6, 9, 12))
        assert state == "new" and alert is None

    def test_late_fires_once(self):
        job = _job(last_ping_at="2026-06-09T12:00:00+00:00", last_status="success", state="up")
        state, alerted, alert = evaluate(job, at(2026, 6, 9, 14))
        assert state == "late"
        assert isinstance(alert, Alert) and alert.state == "late"
        assert alerted == "late"

    def test_late_not_repeated_when_already_alerted(self):
        job = _job(last_ping_at="2026-06-09T12:00:00+00:00", last_status="success",
                  state="late", alerted_state="late")
        state, alerted, alert = evaluate(job, at(2026, 6, 9, 14))
        assert state == "late" and alert is None

    def test_failed_fires(self):
        job = _job(last_ping_at="2026-06-09T12:00:00+00:00", last_status="fail",
                  state="up", last_exit_code=1)
        state, alerted, alert = evaluate(job, at(2026, 6, 9, 12, 1))
        assert state == "failed" and alert.state == "failed"
        assert "exit 1" in alert.detail

    def test_recovery_after_alert(self):
        job = _job(last_ping_at="2026-06-09T13:00:00+00:00", last_status="success",
                  state="late", alerted_state="late")
        state, alerted, alert = evaluate(job, at(2026, 6, 9, 13, 5))
        assert state == "up"
        assert alert is not None and alert.recovery is True
        assert alerted is None

    def test_paused_never_alerts(self):
        job = _job(paused=1, last_ping_at="2026-06-09T12:00:00+00:00",
                  last_status="fail", state="up")
        state, alerted, alert = evaluate(job, at(2026, 6, 9, 20))
        assert alert is None


class TestSizeAnomaly:
    def test_needs_min_history(self):
        assert size_anomaly([100, 100], 999999) is False

    def test_stable_sizes_no_anomaly(self):
        assert size_anomaly([100, 102, 98, 101], 100) is False

    def test_big_deviation_trips(self):
        assert size_anomaly([100, 100, 100], 200) is True

    def test_empty_dump_against_history_trips(self):
        assert size_anomaly([100, 100, 100], 0) is True

    def test_none_latest_is_safe(self):
        assert size_anomaly([100, 100, 100], None) is False


class TestDurationAnomaly:
    def test_needs_min_history(self):
        assert duration_anomaly([10.0, 10.0], 999.0) is False

    def test_stable_durations_no_anomaly(self):
        assert duration_anomaly([10.0, 11.0, 9.0, 10.0], 10.5) is False

    def test_runaway_duration_trips(self):
        assert duration_anomaly([10.0, 10.0, 10.0], 100.0) is True

    def test_instant_run_against_history_trips(self):
        assert duration_anomaly([10.0, 10.0, 10.0], 0.0) is True
