# argus — CLAUDE.md

> Working name: **argus** (Argus Panoptes, the hundred-eyed watchman).
> TODO before public launch: check name collisions (GitHub, PyPI, Docker Hub, trademark).

## What this is

**The Healthchecks.io of backups.** A hosted-first (with self-hostable OSS core)
observability service where every backup job on every machine reports in:
restic, borg, plain shell scripts — one dashboard, one alerting pipeline.

It answers three questions the free fragmented tools don't answer together:

1. **Did every backup run?** (dead-man's switch per job — silence = alert)
2. **Did it actually succeed?** (exit status + tool-native report parsing)
3. **Does the result look sane?** (size/duration anomaly vs. history)

## Positioning — the anti-Prometheus

The target user CAN build this with restic-exporter + Prometheus + Grafana +
Alertmanager. That stack is free; **the setup is the cost**. argus is the
opposite: one container (self-hosted) or one curl line (hosted), zero config
beyond "here's my job, here's my schedule". Simplicity IS the product.

We do not compete with Prometheus, Grafana, Uptime Kuma, borgmatic, Backrest.
We coexist. Where possible we INTEGRATE (accept their webhooks/outputs)
rather than replace.

## Target user

Self-hosters / homelabbers / indie devs running 2–30 backup jobs across
heterogeneous machines (NAS, VPS, RPi, Proxmox VMs), currently "monitoring"
via cron emails they don't read, or nothing. Found on r/selfhosted,
r/homelab, HN. Buys with a credit card. Allergic to marketing speak.

## Business model (decided, not yet built)

Open-core, Healthchecks.io playbook:
- **OSS core**: full single-user functionality, self-hosted, free forever. AGPL-3.0.
- **Hosted version** (the actual product): convenience, no maintenance,
  off-site by definition (a backup monitor on the same box as the backups
  is watching itself die). Target €5–9/mo prosumer, €15–29/mo small team.
- OSS repo + README = the distribution channel. No ads, no influencer marketing.

Validation gates before building hosted version: see DECISIONS D-007.

## MVP scope

### IN (v0.1)
- Job registry: name, expected schedule (cron expr or "every N hours"), grace period
- Per-job ingest URL (secret token in path, Healthchecks-style)
- Ingest, 3 flavors:
  - **generic**: POST with exit code, optional bytes/duration/log tail (works from any shell script in one curl line)
  - **restic**: parse `restic backup --json` summary output
  - **borg**: parse `borg create --json` output
- Dead-man's switch: job silent past schedule+grace → alert
- Failure alert: nonzero exit / tool-reported error → alert
- Size anomaly: latest backup size deviates > X% from rolling median → warning (simple rule, no ML)
- Alert channels: **ntfy** and **Telegram** (SMTP deferred)
- Dashboard: single server-rendered page — all jobs, status, last seen, size sparkline
- Single admin auth (one token/password). No multi-user.
- Deploy: single Docker container, SQLite inside, ARM64 + AMD64 images, docker-compose example
- Docs: README good enough to BE the launch post

### OUT (explicitly deferred — do not creep)
- Duplicati / ZFS snapshots / Proxmox Backup Server / Veeam / kopia parsers → v0.2+ by demand
- Prometheus /metrics exporter → v0.2 (integration play, cheap, but not MVP)
- Restore-test orchestration → future (reminder nudges first, orchestration much later)
- Multi-user, orgs, RBAC → hosted version only, later
- SMTP alerts, Discord, Slack → later (PRs welcome)
- Any enterprise backup tool (NetBackup, Commvault…) → NEVER (wrong market, see FAILURES F-002)
- LLM features → not in MVP. Possible later: log-tail failure summarization. Not a wrapper product.

## Stack & conventions

- Python 3.12, **FastAPI**, **SQLite** (WAL), APScheduler for the dead-man sweep
- Server-rendered UI: Jinja2 + **HTMX** + minimal CSS. No React/Next for the OSS core —
  one container, low RAM (RPi-friendly) is part of the product promise
- **TDD**: tests before code, pytest. First slice must ship with tests
- Code, comments, docs, commits: **English**. Conversation: Italian
- Docker image: distroless or slim, < 150 MB target
- Repo docs: this file + DECISIONS.md + FAILURES.md + STATE.md + HANDOFF.md (ANTIPATTERNS.md when earned)

## Budget reality (constraint: ≤ €2,000 total, target ≪ that)

- MVP costs: domain (~€10/yr) + €0 infra (runs on existing homelab/devbox for dev)
- Hosted alpha later: 1 small VPS (~€5/mo) — only after validation gates pass
- Biggest spend is weekends, not money. Estimate: 3–4 weekends to launchable MVP.

## North star

This is a **side project with a kill switch**, not a startup. Day job stays.
Honest comparables (Healthchecks.io, Simple Analytics): years to meaningful
revenue, ~$700/mo plateaus are normal early. The bet is cheap because Roberto
would build this for his own homelab anyway — dogfooding is guaranteed.
