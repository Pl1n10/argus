# argus

**The Healthchecks.io of backups.** Every backup job — `restic`, `borg`, or a
plain shell script — reports in to one place. argus answers the three questions
your scattered cron emails don't answer together:

1. **Did every backup run?** — a dead-man's switch per job: silence past the
   schedule is an alert.
2. **Did it actually succeed?** — exit status, plus native parsing of restic /
   borg output.
3. **Does the result look sane?** — a size deviates wildly from its own history
   → warning (empty dump, runaway growth, truncated archive).

One container. SQLite inside. A server-rendered dashboard. Alerts to **ntfy** or
**Telegram**. That's the whole thing.

> **Why not Prometheus + Grafana + Alertmanager + an exporter?** You can build
> this with that stack, for free. *The setup is the cost.* argus is the
> opposite: `docker run`, then one `curl` line per job. Simplicity is the point.
> Where it can, argus *integrates* with your tools rather than replacing them.

---

## Quickstart

```bash
docker run -d --name argus -p 8000:8000 -v argus-data:/data \
  -e ARGUS_ADMIN_TOKEN=changeme \
  -e ARGUS_BASE_URL=https://argus.example.com \
  ghcr.io/pl1n10/argus:latest    # or build locally: docker build -f docker/Dockerfile -t argus-backup .
```

Open `http://localhost:8000/?token=changeme`. Then register a job:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Authorization: Bearer changeme" \
  -d '{"name":"nightly-restic","schedule_kind":"interval","schedule_expr":"86400","grace_seconds":3600}'
# → { "ingest_url": "https://argus.example.com/ingest/<secret-token>", ... }
```

`schedule_kind` is `interval` (`schedule_expr` = seconds between runs) or `cron`
(`schedule_expr` = a 5-field cron expression). `grace_seconds` is how late a run
may be before argus alerts.

## Wiring up a backup job

**Any shell script** — append one line. A bare hit means "ran, exit 0":

```bash
restic backup /data ; curl -fsS "https://argus.example.com/ingest/<token>?exit_code=$?"
```

**restic**, with native parsing of size and duration:

```bash
restic backup /data --json | tail -n1 | \
  curl -fsS "https://argus.example.com/ingest/<token>?flavor=restic" --json @-
```

**borg**:

```bash
borg create --json ::'{now}' /data | \
  curl -fsS "https://argus.example.com/ingest/<token>?flavor=borg" --json @-
```

That's it. argus now knows when the job last ran, whether it succeeded, and how
big the result was — and pages you when one of those goes wrong.

## Alerts

Set any of these env vars to enable a channel (unset = disabled):

| Variable | Channel |
|---|---|
| `ARGUS_NTFY_URL` | ntfy topic URL, e.g. `https://ntfy.sh/my-backups` |
| `ARGUS_TELEGRAM_BOT_TOKEN` + `ARGUS_TELEGRAM_CHAT_ID` | Telegram bot |

Alerts are edge-triggered: argus pages you **once** when a job goes late or
fails, and once more when it recovers — never every minute.

## docker-compose

A ready example is in [`docker-compose.yml`](./docker-compose.yml):

```bash
echo "ARGUS_ADMIN_TOKEN=$(openssl rand -hex 16)" > .env
docker compose up -d
```

> **Run argus off-site.** A backup monitor on the same box as the backups is
> watching itself die. Put it on a different node, a cheap VPS, anywhere your
> jobs can reach outbound.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `ARGUS_DB` | `argus.db` | SQLite file path |
| `ARGUS_ADMIN_TOKEN` | _(none)_ | Guards the dashboard and job API. Unset = open (dev only). |
| `ARGUS_BASE_URL` | `http://localhost:8000` | Public URL, used to print ingest URLs |
| `ARGUS_NTFY_URL` | _(none)_ | ntfy alert channel |
| `ARGUS_TELEGRAM_BOT_TOKEN` / `ARGUS_TELEGRAM_CHAT_ID` | _(none)_ | Telegram alert channel |

## Status

**v0.1, single-user, self-hostable, free forever (AGPL-3.0).** This is the open
core. A hosted version — zero maintenance, off-site by definition — is planned.
Want it? **Leave your email and I'll tell you when it's ready:** _(waitlist link
coming with the launch post)._

Parser requests (kopia, Duplicati, PBS, ZFS snapshots, …) are very welcome — open
an issue. Each one tells me what to build next.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest          # 84 tests, all offline (no network, no real scheduler)
ruff check .
argus serve     # http://127.0.0.1:8000
```

## License

[AGPL-3.0-or-later](./LICENSE). Free for self-hosters; the copyleft keeps a
cloud provider from reselling argus-as-a-service without contributing back.
