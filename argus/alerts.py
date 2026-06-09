"""Alert channels: ntfy and Telegram (D-006). SMTP deferred (DMARC pain).

A channel is anything with `.send(subject, body)`. Concrete channels post over
HTTP via an injected httpx.Client (so tests use httpx.MockTransport, never the
network — global rule). `notify` fans out and never lets one dead channel break
the others: a backup monitor that crashes on a flaky push is worse than useless.
"""
from __future__ import annotations

import logging
from typing import Protocol

import httpx

from argus.checks import Alert

log = logging.getLogger("argus.alerts")

# Emoji-free is a choice: some ntfy/Telegram setups mangle them, and the audience
# values plain text. The state word carries the signal.
_PREFIX = {"late": "[LATE]", "failed": "[FAILED]", "up": "[OK]"}


def format_alert(alert: Alert) -> tuple[str, str]:
    """Render an Alert into (subject, body). Pure; shared by every channel."""
    prefix = _PREFIX.get(alert.state, "[ALERT]")
    subject = f"{prefix} {alert.job_name}"
    body = f"{alert.job_name}: {alert.detail}" if alert.detail else alert.job_name
    return subject, body


class Channel(Protocol):
    def send(self, subject: str, body: str) -> None: ...


class NtfyChannel:
    """POST to an ntfy topic URL. Subject becomes the ntfy Title header."""

    def __init__(self, url: str, client: httpx.Client):
        self.url = url
        self._client = client

    def send(self, subject: str, body: str) -> None:
        self._client.post(self.url, content=body.encode("utf-8"),
                          headers={"Title": subject}, timeout=10)


class TelegramChannel:
    """sendMessage via the Bot API. Token + chat_id from config."""

    def __init__(self, bot_token: str, chat_id: str, client: httpx.Client):
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id
        self._client = client

    def send(self, subject: str, body: str) -> None:
        self._client.post(self._url, json={
            "chat_id": self._chat_id,
            "text": f"{subject}\n{body}",
        }, timeout=10)


def build_channels(config: dict, client: httpx.Client | None = None) -> list[Channel]:
    """Construct the configured channels. Unset config = channel disabled.

    config keys: ntfy_url, telegram_bot_token, telegram_chat_id.
    """
    client = client or httpx.Client()
    channels: list[Channel] = []
    if config.get("ntfy_url"):
        channels.append(NtfyChannel(config["ntfy_url"], client))
    if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
        channels.append(TelegramChannel(
            config["telegram_bot_token"], config["telegram_chat_id"], client))
    return channels


def notify(channels: list[Channel], alert: Alert) -> None:
    """Send one alert to every channel, isolating failures."""
    subject, body = format_alert(alert)
    for ch in channels:
        try:
            ch.send(subject, body)
        except Exception:  # noqa: BLE001 — a flaky channel must not break the sweep
            log.exception("alert channel %s failed", type(ch).__name__)
