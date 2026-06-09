# argus — DECISIONS.md

Numbered ADRs. Never delete; supersede with a new entry.

---

## D-001 — Push-based ingestion (jobs report in), not pull/agent

**Decision:** Backup jobs POST their result to a per-job URL. No polling
agent, no SSH into machines, no scraping.

**Why:** (a) Homelab machines live behind NAT/CGNAT — pull is a firewall
nightmare, push works from anywhere outbound. (b) Push gives the dead-man's
switch for free: silence is the signal. (c) Proven by Healthchecks.io at
scale. (d) One-curl-line integration = lowest possible setup cost, which is
the product's whole thesis.

**Tradeoff accepted:** a compromised job token can spam false "OK"s. Fine
for this threat model.

---

## D-002 — SQLite, not Postgres

**Decision:** SQLite (WAL mode) for the OSS core.

**Why:** Single-container promise; RPi-class hardware; write volume is
trivial (even 100 jobs × hourly = nothing). Same decision already made and
validated in linkedin-job-agent and pocket-dnd. Postgres reconsidered only
for the hosted multi-tenant version (separate codepath decision, later).

---

## D-003 — FastAPI + Jinja2/HTMX single container, no JS framework

**Decision:** Server-rendered dashboard in the same FastAPI app. No
Next.js/React for the OSS core.

**Why:** The deploy story ("docker run, open browser") is the differentiator
vs. the Prometheus stack. A second container or a node build chain erodes
it. HTMX covers the needed interactivity (status refresh, sparklines via
inline SVG). Roberto knows Next.js — this is a product decision, not a
skill gap.

---

## D-004 — MVP parsers: generic + restic + borg only

**Decision:** Three ingest flavors in v0.1. Everything else deferred.

**Why:** restic and borg dominate r/selfhosted backup threads; the generic
endpoint catches literally everything else (any script, any tool, any OS)
at lower fidelity. Each additional native parser is post-launch, demand-driven
— parser requests in GitHub issues are themselves a validation signal.
Per-tool parsers accumulated over time are the moat (Bank Statement
Converter pattern: the edge-case knowledge IS the product).

---

## D-005 — License: AGPL-3.0 for the OSS core

**Decision:** AGPL-3.0.

**Why:** Protects the hosted business from a cloud provider (or anyone)
offering argus-as-a-service without contributing back, while remaining
genuinely free for self-hosters. Plausible-validated playbook.
**Tradeoff:** a slice of devs avoids AGPL; acceptable — they are
self-hosters (served by the free core), not hosted-version buyers.

---

## D-006 — MVP alert channels: ntfy + Telegram

**Decision:** Two channels at launch.

**Why:** ntfy is the self-hosted community's darling (and itself
self-hostable — coherent with audience values); Telegram bot code already
battle-tested by Roberto (croccantini-watcher). SMTP deferred: deliverability
pain, DMARC yak-shaving (see the GitLab issue that motivated this product —
their email alerts died of DMARC).

---

## D-007 — Validation-first: OSS launch gates the hosted build

**Decision:** Build hosted version ONLY if, within ~60 days of the
r/selfhosted + Show HN launch:
- GitHub stars ≥ 150, **or**
- hosted-waitlist signups ≥ 30, **or**
- organic parser requests / PRs from ≥ 10 distinct users.

Below ALL thresholds after one positioning retry → freeze as personal tool,
zero regrets (it runs Roberto's homelab anyway). These numbers are
heuristics, not gospel — but they are written down BEFORE launch to keep
hope from doing the accounting (measured behavior > stated opinions;
survey-style validation explicitly rejected, see FAILURES F-003).

---

## D-008 — Size anomaly detection: simple rule, no ML

**Decision:** Warning when latest size deviates more than a configurable %
(default ±30%) from the rolling median of the last N (default 10) runs.
Duration: same rule, warn-only.

**Why:** Transparent, explainable, zero dependencies, covers the real cases
(empty dump, runaway growth, truncated archive). ML here is over-engineering
— the exact failure mode this project's owner has a documented allergy to.

---

## D-009 — The hosted version is the product; OSS is the distribution

**Decision:** Treat the OSS repo + README as the entire marketing function.
No content treadmill, no social presence requirements. README quality,
launch post quality, and parser breadth are the only growth levers in year 1.

**Why:** Matches founder's documented weakness (distribution/marketing) to
a channel that rewards what he's actually good at (engineering quality +
written documentation). Pattern validated by Healthchecks.io, Plausible,
Uptime Kuma (distribution side).

---

## D-010 — Name: "argus" is the working/repo name; publishable IDs use a compound

**Decision:** Keep `argus` as the GitHub repo name (under the `Pl1n10`
namespace — `Pl1n10/argus` — already created) and as the internal Python
import package (`argus/`). But every GLOBALLY-shared identifier uses the
compound **`argus-backup`**: PyPI distribution name, Docker image name, and
the eventual domain (`argusbackup.*` / `getargus.*`).

**Why:** Collision check (2026-06-09) found "argus" saturated in the exact
monitoring/observability space — PyPI `argus`/`argus-server`/`argus-api` all
taken; GitHub crowded (Uninett/Argus alert aggregator, release-argus.io,
openargus sensor, several observability repos); Docker Hub `argus` taken.
A namespaced GitHub repo is unaffected, but an un-namespaced PyPI/Docker/domain
name is not — claiming the compound now avoids a painful rename after launch.

**Tradeoff:** the binary/product is colloquially "argus" while it ships as
`argus-backup`. Acceptable; Healthchecks.io ships as `healthchecks` the repo
but `healthchecks.io` the product — same split. Final public name is
re-confirmable before the r/selfhosted launch (this decision is publish-gated,
not code-gated; building proceeds under `Pl1n10/argus`).
