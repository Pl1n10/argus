"""End-to-end of the monitoring loop over a real (in-memory) Store: a ping
flips state, the sweep arms the dead-man's switch, alerts fire exactly once."""
from argus.ingest import PingData
from argus.monitor import evaluate_job, sweep
from tests.conftest import at


def _make(store):
    return store.create_job(name="nightly", schedule_kind="interval",
                            schedule_expr="3600", grace_seconds=600)


def test_successful_ping_sets_up_no_alert(store, channel):
    job = _make(store)
    fresh = store.record_ping(job["id"], PingData("success", "generic", exit_code=0),
                              now=at(2026, 6, 9, 12))
    evaluate_job(store, fresh, [channel], now=at(2026, 6, 9, 12))
    assert store.get_job(job["id"])["state"] == "up"
    assert channel.sent == []


def test_failed_ping_alerts(store, channel):
    job = _make(store)
    fresh = store.record_ping(job["id"], PingData("fail", "generic", exit_code=2),
                              now=at(2026, 6, 9, 12))
    evaluate_job(store, fresh, [channel], now=at(2026, 6, 9, 12))
    assert store.get_job(job["id"])["state"] == "failed"
    assert len(channel.sent) == 1
    assert "[FAILED]" in channel.sent[0][0]


def test_sweep_turns_silence_into_late_once(store, channel):
    job = _make(store)
    store.record_ping(job["id"], PingData("success", "generic", exit_code=0),
                      now=at(2026, 6, 9, 12))
    evaluate_job(store, store.get_job(job["id"]), [channel], now=at(2026, 6, 9, 12))

    # 2h later, well past 13:00 + 600s grace -> late, one alert
    fired = sweep(store, [channel], now=at(2026, 6, 9, 14))
    assert [a.state for a in fired] == ["late"]
    assert store.get_job(job["id"])["state"] == "late"

    # sweeping again must NOT re-alert
    fired2 = sweep(store, [channel], now=at(2026, 6, 9, 14, 30))
    assert fired2 == []
    assert len(channel.sent) == 1


def test_recovery_after_late(store, channel):
    job = _make(store)
    store.record_ping(job["id"], PingData("success", "generic"), now=at(2026, 6, 9, 12))
    evaluate_job(store, store.get_job(job["id"]), [channel], now=at(2026, 6, 9, 12))
    sweep(store, [channel], now=at(2026, 6, 9, 14))  # -> late

    # a new ping arrives -> recovery alert
    fresh = store.record_ping(job["id"], PingData("success", "generic"), now=at(2026, 6, 9, 14, 30))
    evaluate_job(store, fresh, [channel], now=at(2026, 6, 9, 14, 30))
    assert store.get_job(job["id"])["state"] == "up"
    assert "[OK]" in channel.sent[-1][0]


def _ping(store, channel, job_id, bytes_, hour):
    fresh = store.record_ping(job_id, PingData("success", "generic", exit_code=0, bytes=bytes_),
                              now=at(2026, 6, 9, hour))
    evaluate_job(store, fresh, [channel], now=at(2026, 6, 9, hour))


def test_size_anomaly_alerts_once_then_clears(store, channel):
    job = _make(store)
    for h, b in [(1, 100), (2, 100), (3, 100)]:  # normal history, no anomaly
        _ping(store, channel, job["id"], b, h)
    assert channel.sent == []

    _ping(store, channel, job["id"], 1000, 4)  # 10x jump -> warn, once
    warns = [s for s in channel.sent if s[0].startswith("[WARN]")]
    assert len(warns) == 1

    _ping(store, channel, job["id"], 1000, 5)  # still anomalous vs median, no repeat
    assert len([s for s in channel.sent if s[0].startswith("[WARN]")]) == 1

    _ping(store, channel, job["id"], 100, 6)   # back to normal -> flag clears
    _ping(store, channel, job["id"], 1000, 7)  # anomalous again -> fires again
    assert len([s for s in channel.sent if s[0].startswith("[WARN]")]) == 2


def test_paused_job_never_alerts(store, channel):
    job = _make(store)
    store.record_ping(job["id"], PingData("fail", "generic", exit_code=1), now=at(2026, 6, 9, 12))
    store.set_paused(job["id"], True)
    sweep(store, [channel], now=at(2026, 6, 9, 20))
    assert channel.sent == []
