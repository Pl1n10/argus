import httpx

from argus.alerts import (
    NtfyChannel,
    TelegramChannel,
    build_channels,
    format_alert,
    notify,
)
from argus.checks import Alert
from tests.conftest import RecordingChannel


def _mock_client(record: list[httpx.Request]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        record.append(request)
        return httpx.Response(200)
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestFormat:
    def test_late_subject(self):
        subj, body = format_alert(Alert("nightly", "late", detail="no report"))
        assert subj == "[LATE] nightly"
        assert "no report" in body

    def test_recovery(self):
        subj, _ = format_alert(Alert("nightly", "up", detail="recovered", recovery=True))
        assert subj == "[OK] nightly"


class TestNtfy:
    def test_posts_body_and_title(self):
        seen: list[httpx.Request] = []
        ch = NtfyChannel("https://ntfy.sh/mytopic", _mock_client(seen))
        ch.send("[LATE] nightly", "nightly: no report")
        assert len(seen) == 1
        assert seen[0].headers["Title"] == "[LATE] nightly"
        assert seen[0].content == b"nightly: no report"


class TestTelegram:
    def test_posts_chat_id_and_text(self):
        seen: list[httpx.Request] = []
        ch = TelegramChannel("BOTTOKEN", "12345", _mock_client(seen))
        ch.send("[FAILED] db", "db: exit 1")
        assert "/botBOTTOKEN/sendMessage" in str(seen[0].url)


class TestBuildChannels:
    def test_only_configured_channels(self):
        chans = build_channels({"ntfy_url": "https://ntfy.sh/t"}, client=_mock_client([]))
        assert len(chans) == 1 and isinstance(chans[0], NtfyChannel)

    def test_telegram_needs_both_token_and_chat(self):
        chans = build_channels({"telegram_bot_token": "x"}, client=_mock_client([]))
        assert chans == []

    def test_empty_config_no_channels(self):
        assert build_channels({}, client=_mock_client([])) == []


class TestNotify:
    def test_fans_out(self):
        a, b = RecordingChannel(), RecordingChannel()
        notify([a, b], Alert("nightly", "late", detail="x"))
        assert len(a.sent) == 1 and len(b.sent) == 1

    def test_one_failure_does_not_break_others(self):
        class Boom:
            def send(self, *a):
                raise RuntimeError("down")
        good = RecordingChannel()
        notify([Boom(), good], Alert("nightly", "late"))
        assert len(good.sent) == 1
