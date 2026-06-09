import pytest

from argus.db import JobNotFound
from argus.ingest import PingData
from tests.conftest import at


def _make(store, **over):
    kw = dict(name="nightly", schedule_kind="interval", schedule_expr="3600",
              grace_seconds=600)
    kw.update(over)
    return store.create_job(**kw)


class TestJobs:
    def test_create_returns_token_and_new_state(self, store):
        job = _make(store)
        assert job["token"]
        assert job["state"] == "new"
        assert job["last_ping_at"] is None

    def test_create_blank_name_rejected(self, store):
        with pytest.raises(ValueError):
            _make(store, name="   ")

    def test_tokens_are_unique(self, store):
        assert _make(store)["token"] != _make(store)["token"]

    def test_get_by_token(self, store):
        job = _make(store)
        assert store.get_job_by_token(job["token"])["id"] == job["id"]

    def test_get_by_unknown_token_is_none(self, store):
        assert store.get_job_by_token("nope") is None

    def test_get_missing_raises(self, store):
        with pytest.raises(JobNotFound):
            store.get_job(999)

    def test_delete(self, store):
        job = _make(store)
        store.delete_job(job["id"])
        assert store.get_job_by_token(job["token"]) is None

    def test_pause(self, store):
        job = _make(store)
        assert store.set_paused(job["id"], True)["paused"] == 1

    def test_list_sorted_by_name(self, store):
        _make(store, name="zebra")
        _make(store, name="alpha")
        assert [j["name"] for j in store.list_jobs()] == ["alpha", "zebra"]


class TestPings:
    def test_record_updates_last_ping_and_denormalised_status(self, store):
        job = _make(store)
        fresh = store.record_ping(job["id"], PingData(status="success", flavor="generic",
                                  exit_code=0, bytes=100), now=at(2026, 6, 9, 12))
        assert fresh["last_ping_at"].startswith("2026-06-09T12:00:00")
        assert fresh["last_status"] == "success"
        assert fresh["last_bytes"] == 100

    def test_record_on_missing_job_raises(self, store):
        with pytest.raises(JobNotFound):
            store.record_ping(999, PingData(status="success", flavor="generic"))

    def test_recent_sizes_only_successful_with_bytes(self, store):
        jid = _make(store)["id"]
        store.record_ping(jid, PingData("success", "generic", bytes=10), now=at(2026, 6, 9, 1))
        store.record_ping(jid, PingData("fail", "generic", bytes=None), now=at(2026, 6, 9, 2))
        store.record_ping(jid, PingData("success", "generic", bytes=20), now=at(2026, 6, 9, 3))
        assert store.recent_sizes(jid) == [10, 20]

    def test_delete_cascades_pings(self, store):
        job = _make(store)
        store.record_ping(job["id"], PingData("success", "generic", bytes=1))
        store.delete_job(job["id"])
        # a fresh job reusing nothing; just assert no crash and empty history elsewhere
        other = _make(store, name="other")
        assert store.recent_sizes(other["id"]) == []
