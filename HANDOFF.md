# argus — HANDOFF.md

For the next session (Claude or human). Read CLAUDE.md → DECISIONS.md →
FAILURES.md → STATE.md first. Scope is frozen; resist creep.

## Done (ahead of the original HANDOFF plan)

- **Step 1** — name collision check → D-010 (publish under `argus-backup`; the
  Debian `argus`/`argus-clients` network monitor is the sharpest collision).
- **Step 2** — repo scaffold + CI (ruff + pytest + multi-arch docker build).
- **Step 3** — first vertical slice, TDD. Jobs API, ingest (generic/restic/borg),
  dead-man sweep, failure + recovery alerts (ntfy/Telegram), dashboard, auth.
- **Step 5** (pulled forward) — restic+borg parsers, **size AND duration anomaly
  that actually alert** (warn-level, edge-triggered, D-008), Telegram, sparkline.
- **CI + Publish green.** Image `ghcr.io/pl1n10/argus-backup:latest` (amd64+arm64)
  is **verified public** — confirmed with a `docker pull` under an empty
  `DOCKER_CONFIG` (zero creds). README quickstart works as written.
- **Review-hardened:** anomaly alerting, log_tail/body caps (D-011), timing-safe
  admin compare, name coherence, README portability (restic exit-code wrapper,
  older-curl flags, `?token=` log caveat).

**93 tests, all offline, ruff clean.** Verify the suite:
```bash
.venv/bin/ruff check . && .venv/bin/pytest
```

## ▶ NEXT: Step 4 — Dogfooding (the real definition-of-done)

This is where the project goes from "green tests" to "earns trust on real
hardware." See the split TODO below.

---

## TODO — owner (Roberto)  ⟶ needs your machines / accounts / wall-clock

- [ ] **Wire real backups** to argus ingest URLs: cnosso cluster (gaia/urano),
      devbox, the VPS. One job per real backup; use the README snippets.
- [ ] **Symbolic first migration:** replace the croccantini-watcher dead-man's
      switch with an argus job. (Proves the "replaces my hand-rolled monitor"
      story — the one that sells on r/selfhosted.)
- [ ] **Run the 7-day soak.** Mid-way, deliberately induce one failure and
      confirm the alert fires end-to-end. That closes Step 3's wall-clock DoD.
- [ ] Log every friction as a GitHub issue on self (issues are launch material).
- [ ] **Screenshots** of the live dashboard for the README.
- [ ] **Waitlist** link (Plausible or a plain form) into the README placeholder.
- [ ] **Launch:** r/selfhosted "I built this" + Show HN. Measure vs D-007 gates
      at day 30 and day 60. No vibes.
- [ ] Before heavy promotion: confirm/registrate the final public name + domain
      (`argusbackup.*`, D-010).

## TODO — next session (Claude / agent)  ⟶ doable without you present

- [ ] When you start dogfooding, hand me your actual backup commands per host and
      I'll produce copy-paste ingest wrappers (restic/borg/script, exit-code-safe).
- [ ] Parser requests arriving as issues → add native parsers, demand-driven,
      with tests (D-004; each is a validation signal + the moat).
- [ ] Optional hardening: cap a **chunked** ingest body by reading the stream with
      a hard byte limit (closes the D-011 known gap) — only if argus ends up
      exposed without a fronting proxy.
- [ ] Optional polish (deferred, issues-not-now): per-job history/detail view,
      duration sparkline, SMTP/Discord channels, Prometheus `/metrics`.
- [ ] Keep STATE.md + HANDOFF.md current at each step.

## Deferred (do NOT creep — issues, not now)

SMTP/Discord/Slack, Prometheus exporter, more parsers (kopia/Duplicati/PBS/ZFS —
demand-driven), multi-user/orgs/RBAC. See CLAUDE.md OUT list.

---

### Standing rules for every session

- Tests before code. English in repo, Italian in chat.
- Any scope addition → must displace something or go to a "later" issue.
- Any discarded approach → FAILURES.md entry, same day.
- Update STATE.md at session end. HANDOFF update is part of the step commit.
- Identity: Pl1n10 / robnovara@gmail.com. Push authorized for this project.
