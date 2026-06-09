# argus — HANDOFF.md

For the next session (Claude or human). Read CLAUDE.md → DECISIONS.md →
FAILURES.md → STATE.md first. Scope is frozen; resist creep.

## Done so far

- **Step 1** — name collision check → D-010 (compound `argus-backup` for
  PyPI/Docker/domain; repo `Pl1n10/argus` is fine, namespaced).
- **Step 2** — repo scaffold + CI (ruff + pytest + multi-arch docker build).
- **Step 3** — first vertical slice, TDD, 84 tests green, ruff clean, real boot
  smoke-tested. Jobs API, ingest (generic/restic/borg), dead-man sweep, failure
  + recovery alerts (ntfy/Telegram), dashboard, single-admin auth.
- **Step 5** (pulled forward) — restic+borg parsers, size anomaly (D-008),
  Telegram channel, inline-SVG sparkline: all landed in the slice above.

## How to verify the suite is green

```bash
.venv/bin/ruff check . && .venv/bin/pytest
```

All tests are offline: no network (httpx MockTransport / recording channel),
no real APScheduler thread, in-memory SQLite, injected clock.

## Step A — confirm CI green on GitHub (next)

First push triggers `.github/workflows/ci.yml`. Watch the run; if the arm64
docker build is slow or flaky under QEMU, consider splitting it to a separate
trigger. `gh run list` / `gh run watch`.

## Step B — publish the image to GHCR

CI currently builds without pushing. Add a push step (on tags or main) to
`ghcr.io/pl1n10/argus`. Needs `packages: write` permission + login step.

## Step C — Dogfood (the real definition-of-done)

Wire ALL of Roberto's real backups: cnosso cluster (gaia/urano), devbox, VPS,
and replace the croccantini-watcher dead-man's switch with argus (first
migration test). Every friction found = a GitHub issue on self. Then run a
**7-day soak** with one deliberately induced failure caught and alerted
(Step 3's wall-clock definition-of-done).

## Step D — README launch polish + screenshots, then r/selfhosted + Show HN

Waitlist link (placeholder already in README). Measure against D-007 gates at
day 30 and day 60. No vibes.

## Deferred (do not creep — issues, not now)

Duration anomaly, SMTP/Discord/Slack, Prometheus exporter, more parsers
(kopia/Duplicati/PBS/ZFS — demand-driven), multi-user. See CLAUDE.md OUT list.

---

### Standing rules for every session

- Tests before code. English in repo, Italian in chat.
- Any scope addition → must displace something or go to a "later" issue.
- Any discarded approach → FAILURES.md entry, same day.
- Update STATE.md at session end. HANDOFF update is part of the step commit.
- Identity: Pl1n10 / robnovara@gmail.com. Push authorized for this project.
