"""Ingest parsers: turn a posted body into a normalised PingData.

Three flavors in the MVP (D-004):
  - generic: `{exit_code?, bytes?, duration_s?, log_tail?}` — works from any
    shell script in one curl line. A bare/empty body means "ran, exit 0".
  - restic:  the `restic backup --json` summary object (message_type=summary)
             or its error object (message_type=error).
  - borg:    the `borg create --json` object (top-level `archive.stats`).

Each native parser is post-launch demand-driven; the accumulated edge-case
knowledge is the moat (D-004). These are pure functions: no DB, no network.
"""
from __future__ import annotations

from dataclasses import dataclass


class ParseError(ValueError):
    """The body could not be parsed for the declared flavor."""


# A log *tail* is meant to be small; cap it so a chatty (or malicious) job can't
# fill the disk via the open ingest endpoint. Keep the END (most recent lines).
_MAX_LOG_TAIL = 8192


@dataclass
class PingData:
    status: str                      # 'success' | 'fail'
    flavor: str
    exit_code: int | None = None
    bytes: int | None = None         # size of this backup, if reported
    duration_s: float | None = None
    log_tail: str | None = None


def parse(flavor: str, body: dict | None) -> PingData:
    body = body or {}
    if not isinstance(body, dict):
        raise ParseError("body must be a JSON object")
    if flavor == "generic":
        return _generic(body)
    if flavor == "restic":
        return _restic(body)
    if flavor == "borg":
        return _borg(body)
    raise ParseError(f"unknown flavor: {flavor!r}")


def _generic(body: dict) -> PingData:
    # Bare ping = success. exit_code drives status; anything non-zero is a fail.
    exit_code = body.get("exit_code", 0)
    try:
        exit_code = int(exit_code)
    except (TypeError, ValueError) as e:
        raise ParseError(
            f"exit_code must be an integer, got {body.get('exit_code')!r}") from e
    return PingData(
        status="success" if exit_code == 0 else "fail",
        flavor="generic",
        exit_code=exit_code,
        bytes=_opt_int(body.get("bytes")),
        duration_s=_opt_float(body.get("duration_s")),
        log_tail=_log_tail(body.get("log_tail")),
    )


def _restic(body: dict) -> PingData:
    mt = body.get("message_type")
    if mt == "error":
        return PingData(status="fail", flavor="restic",
                        log_tail=_log_tail(body.get("error") or body.get("message")))
    # Accept the summary object explicitly, or any body carrying its key fields.
    if mt not in (None, "summary") and "total_bytes_processed" not in body:
        raise ParseError(f"unexpected restic message_type: {mt!r}")
    if "total_bytes_processed" not in body:
        raise ParseError("restic body is not a summary (no total_bytes_processed)")
    return PingData(
        status="success",
        flavor="restic",
        bytes=_opt_int(body.get("total_bytes_processed")),
        duration_s=_opt_float(body.get("total_duration")),
    )


def _borg(body: dict) -> PingData:
    archive = body.get("archive")
    if not isinstance(archive, dict):
        raise ParseError("borg body has no `archive` object")
    stats = archive.get("stats") or {}
    return PingData(
        status="success",
        flavor="borg",
        bytes=_opt_int(stats.get("original_size")),
        duration_s=_opt_float(archive.get("duration")),
    )


def _opt_int(v: object) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError) as e:
        raise ParseError(f"expected an integer, got {v!r}") from e


def _opt_float(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError) as e:
        raise ParseError(f"expected a number, got {v!r}") from e


def _opt_str(v: object) -> str | None:
    if v is None:
        return None
    return str(v)


def _log_tail(v: object) -> str | None:
    """Stringify and keep only the last _MAX_LOG_TAIL chars (the tail)."""
    s = _opt_str(v)
    if s is None:
        return None
    return s[-_MAX_LOG_TAIL:]
