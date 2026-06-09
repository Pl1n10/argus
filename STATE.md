# argus — STATE.md

**Last updated:** 2026-06-09
**Phase:** 1 — MVP build in progress (first vertical slice GREEN)

## Where we are

- Repo scaffolded and pushed: `Pl1n10/argus`. Python 3.12, FastAPI, SQLite,
  Jinja2, APScheduler, croniter, httpx. Packaging as `argus-backup` (D-010).
- CI: GitHub Actions — ruff + pytest, plus a multi-arch (amd64+arm64) docker build.
- **First vertical slice is done and green (84 tests, ruff clean):**
  - Job registry + per-job ingest token URL (`POST /api/jobs`).
  - Ingest `POST/GET /ingest/{token}` — generic, restic, borg flavors.
  - Dead-man's switch via APScheduler sweep (silence past schedule+grace → LATE).
  - Failure detection (nonzero exit / tool error → FAILED).
  - Size anomaly (D-008 simple-rule, no ML) + inline-SVG sparkline.
  - Alert channels ntfy + Telegram, edge-triggered (alert once, recover once).
  - Server-rendered dashboard `/`, single-admin-token auth.
  - Real boot smoke-tested end-to-end on devbox.
- Name collision check: DONE. D-010 recorded (argus crowded → compound for
  PyPI/Docker/domain; repo namespaced is fine).

## Architecture (as built)

Pure rules (`scheduling`, `ingest`, `checks`) ← service layer (`monitor`,
`db.Store`) ← HTTP (`server.create_app`) + sweep (`__main__` APScheduler).
Everything clock-injectable; tests are fully offline (no network, no real
scheduler, recording fake for alert channels).

## Not started / next

- CI green confirmation on GitHub (pushed; watch the first run).
- Publish image to GHCR (workflow currently builds without pushing).
- Dogfood: wire Roberto's real backups (gaia/urano, devbox, VPS); replace the
  croccantini-watcher dead-man's switch with argus (first migration test).
- 7-day soak with one induced failure (Step 3 definition-of-done — wall-clock).
- Duration anomaly (mirror of size rule), SMTP/Discord (deferred), HTMX
  auto-refresh on the dashboard.
- README waitlist link (placeholder in place), launch posts.

## Reserve candidates (parked, not dead)

- **B — container-update intelligence** (changelog/breaking-change layer over
  Diun/WUD). Revisit if argus validation fails.
- **C — local-LLM practical fit benchmarks**. Low priority.

## Next session starts at

HANDOFF.md → confirm CI green, then dogfood wiring + GHCR publish.
