"""CLI entrypoint: `argus serve`.

Builds the real Store, alert channels, and the APScheduler sweep, then runs
uvicorn. The sweep is what arms the dead-man's switch: every minute it
re-evaluates each job and a silent one past schedule+grace becomes 'late' and
alerts. Config comes from flags or ARGUS_* env vars (12-factor, container-ready).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from argus.alerts import build_channels
from argus.db import Store
from argus.monitor import sweep
from argus.server import build_alert_client, create_app

_SCHEMA = Path(__file__).resolve().parent / "schema.sql"
_SWEEP_SECONDS = 60


def _alert_config_from_env() -> dict:
    return {
        "ntfy_url": os.environ.get("ARGUS_NTFY_URL"),
        "telegram_bot_token": os.environ.get("ARGUS_TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.environ.get("ARGUS_TELEGRAM_CHAT_ID"),
    }


def serve(args: argparse.Namespace) -> None:
    store = Store(db_path=args.db, schema_sql=_SCHEMA.read_text(encoding="utf-8"))
    channels = build_channels(_alert_config_from_env(), client=build_alert_client())

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(lambda: sweep(store, channels), "interval",
                      seconds=_SWEEP_SECONDS, id="argus-sweep", max_instances=1)
    scheduler.start()

    app = create_app(
        store,
        channels,
        base_url=args.base_url,
        admin_token=args.admin_token,
    )
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        scheduler.shutdown(wait=False)


def main() -> None:
    parser = argparse.ArgumentParser(prog="argus", description="backup observability")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("serve", help="run the web server + sweep")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--db", default=os.environ.get("ARGUS_DB", "argus.db"))
    s.add_argument("--base-url", default=os.environ.get("ARGUS_BASE_URL", "http://localhost:8000"))
    s.add_argument("--admin-token", default=os.environ.get("ARGUS_ADMIN_TOKEN"))
    s.set_defaults(func=serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
