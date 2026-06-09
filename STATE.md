# argus — STATE.md

**Last updated:** 2026-06-09
**Phase:** 1 — MVP build in progress (first vertical slice GREEN)

## Where we are

- Repo scaffolded and pushed: `Pl1n10/argus`. Python 3.12, FastAPI, SQLite,
  Jinja2, APScheduler, croniter, httpx. Packaging as `argus-backup` (D-010).
- CI: GitHub Actions — ruff + pytest, plus a multi-arch (amd64+arm64) docker build.
- **CI is green on GitHub** (ruff + pytest + multi-arch docker build, ~2m).
- **Image published + verified public:** `ghcr.io/pl1n10/argus-backup:latest`
  (amd64+arm64), anonymously pullable → README quickstart works as written.
- **Hardened after an external code review** (see below).
- **MVP slice done and green (93 tests, ruff clean):**
  - Job registry + per-job ingest token URL (`POST /api/jobs`).
  - Ingest `POST/GET /ingest/{token}` — generic, restic, borg flavors.
  - Dead-man's switch via APScheduler sweep (silence past schedule+grace → LATE).
  - Failure detection (nonzero exit / tool error → FAILED).
  - Size AND duration anomaly (D-008 simple-rule, no ML) + inline-SVG sparkline.
  - Alert channels ntfy + Telegram, edge-triggered (alert once, recover once).
  - Server-rendered dashboard `/` with 60s live-refresh, single-admin-token auth.
  - Real boot smoke-tested end-to-end on devbox.
- Name collision check: DONE. D-010 recorded (argus crowded → compound for
  PyPI/Docker/domain; repo namespaced is fine).

## Review hardening (2026-06-09, external review)

- Size/duration anomaly now **alerts** (warn-level, edge-triggered), not just
  renders — it was a broken promise vs the dead-man thesis.
- `log_tail` capped to 8 KB + ingest body capped to 64 KB (open endpoint, can't
  let a chatty/hostile job fill the disk).
- Admin token compared with `secrets.compare_digest` (timing-safe).
- GHCR publish workflow added (fixes the dead-on-arrival quickstart).
- Name made coherent on `argus-backup` everywhere published (D-010); recorded
  the Debian `argus`/`argus-clients` network-monitor collision.
- README: restic exit-code wrapper, curl `--data-binary` (older-curl safe),
  `?token=` reverse-proxy-log caveat.

## Architecture (as built)

Pure rules (`scheduling`, `ingest`, `checks`) ← service layer (`monitor`,
`db.Store`) ← HTTP (`server.create_app`) + sweep (`__main__` APScheduler).
Everything clock-injectable; tests are fully offline (no network, no real
scheduler, recording fake for alert channels).

## Not started / next (all need YOU — outward-facing or wall-clock)

- Publish image to GHCR (workflow builds without pushing; first publish is a
  new public artifact → decision is the owner's).
- Dogfood: wire Roberto's real backups (gaia/urano, devbox, VPS); replace the
  croccantini-watcher dead-man's switch with argus (first migration test).
- 7-day soak with one induced failure (Step 3 definition-of-done — wall-clock).
- README waitlist link (placeholder in place), launch posts (r/selfhosted + Show HN).
- Deferred (issues, not now): SMTP/Discord, Prometheus exporter, more parsers.

## Reserve candidates (parked, not dead)

- **B — container-update intelligence** (changelog/breaking-change layer over
  Diun/WUD). Revisit if argus validation fails.
- **C — local-LLM practical fit benchmarks**. Low priority.

## Next session starts at

HANDOFF.md → confirm CI green, then dogfood wiring + GHCR publish.
