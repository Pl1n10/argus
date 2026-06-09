import pytest

from argus.scheduling import ScheduleError, next_expected, validate
from tests.conftest import at


class TestValidate:
    def test_interval_ok(self):
        validate("interval", "3600")

    def test_interval_rejects_zero(self):
        with pytest.raises(ScheduleError):
            validate("interval", "0")

    def test_interval_rejects_nonint(self):
        with pytest.raises(ScheduleError):
            validate("interval", "nightly")

    def test_cron_ok(self):
        validate("cron", "0 3 * * *")

    def test_cron_rejects_garbage(self):
        with pytest.raises(ScheduleError):
            validate("cron", "every tuesday")

    def test_unknown_kind(self):
        with pytest.raises(ScheduleError):
            validate("weekly", "x")


class TestNextExpected:
    def test_interval_adds_seconds(self):
        nxt = next_expected("interval", "3600", at(2026, 6, 9, 12, 0, 0))
        assert nxt == at(2026, 6, 9, 13, 0, 0)

    def test_cron_daily_3am(self):
        # after noon, the next 3am run is the following day
        nxt = next_expected("cron", "0 3 * * *", at(2026, 6, 9, 12, 0, 0))
        assert nxt == at(2026, 6, 10, 3, 0, 0)
