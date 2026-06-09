# argus — FAILURES.md

Approaches already tried/researched and discarded. **Do not re-propose these.**
Seeded from the market-research phase (June 2026) so future sessions don't
relitigate settled questions. Sources: 3 independent research passes
(Claude deep research, GPT ideation, DeepSeek agentic) + targeted web
verification of every surviving candidate.

---

## F-001 — Generic format-conversion product (RTF/DOC/PDF converters)

**Tried:** "RTF Modernizer API" and similar format-translation ideas.
**Why it failed:** Format conversion alone is a commodity — free libraries
and built-in tools (Word, Google Docs) do it. Zero willingness to pay.
Value only exists in DOMAIN LOGIC on top of a format (cf. Bank Statement
Converter: per-bank layout knowledge, not "PDF→CSV").
**Lesson:** the format is never the product; the accumulated edge-case
knowledge for a paying audience is.

## F-002 — Enterprise/MSP backup market as the target

**Tried:** "Backup Report Parser for MSPs" (the strongest GPT-doc idea).
**Why it failed for us:** Market IS validated (Backup Radar: $99–649/mo,
5,000+ businesses, acquired by ScalePad) — but (a) incumbent is strong and
well-funded; (b) Roberto's enterprise backup experience is NetBackup-in-a-bank
("campana di vetro") — the MSP world runs Veeam/Datto/MSP360 with commercial
dynamics and communities he has no standing in; (c) banks/enterprises don't
buy via credit card (procurement walls) and MSP distribution runs through
r/msp community presence. Documented incumbent weaknesses (non-self-service
parsing rules, heavy setup, outages) noted for the record — could matter to
someone else, not to us.
**Lesson:** a validated market you can't reach loses to a smaller one you live in.

## F-003 — Survey-style validation ("would you pay?" posts/polls)

**Tried:** Proposed a r/selfhosted validation poll.
**Why it failed:** Stated preference ≠ revealed preference (Mom Test).
People say yes for free and never pay. Roberto called this himself.
**Replacement:** behavior-based validation — ship minimal OSS, measure
stars/installs/waitlist (thresholds in D-007). Passive complaint-mining of
EXISTING spontaneous threads is acceptable evidence; prompted opinions are not.

## F-004 — Generic LLM observability / AI-wrapper products

**Tried:** "LLMOps tooling" zone (Roberto's rare-skill area) and AI-wrapper ideas.
**Why it failed:** Generic LLM observability is saturated with funded
open-source (Langfuse: MIT, 19k+ stars, YC; Helicone: acquired by
ClickHouse; OpenLIT, etc.) — no solo entry at the generic layer. Thin AI
wrappers churn catastrophically (RevenueCat 2026: 21.1% annual retention
vs 30.7% non-AI). LLM skills stay as a possible FEATURE inside argus
(log-tail summarization, someday), never as the product.

## F-005 — Backup-as-a-Service for Supabase/Neon

**Tried:** DeepSeek's "build it in a week, $5–15K MRR" candidate.
**Why it failed:** Supabase Pro ($25/mo — the de-facto production tier)
already bundles daily backups with 7-day retention; Team has 14 days.
Remaining pain (free-tier users, longer retention, exit-strategy copies) is
a niche-of-a-niche with high platform risk: one retention bump by Supabase
kills the product.
**Lesson:** check what the platform bundles BEFORE pricing the gap.

## F-006 — Pure SEO/affiliate content, courses, audience-gated digital products

**Tried:** evaluated across all three research passes.
**Why it failed:** AI Overviews collapsed organic CTR (−61% when present);
affiliate sites hit hardest by 2026 core updates. Templates/courses/
newsletters are audience-gated — they monetize a following Roberto neither
has nor wants to build. "Zero work after creation" claims (DeepSeek doc)
are marketing fiction.
**Lesson:** every model that requires becoming a content creator is
disqualified by founder fit, regardless of TAM.

## F-007 — Selling the TOOL itself in the self-hosted niche

**Tried:** considered paid homelab tools.
**Why it failed:** the niche self-heals with free OSS at remarkable speed —
Watchtower (24.5k stars) archived 2025-12-17, and within weeks the gap was
filled by a community fork, WUD, Diun, Dockwatch, Tugtainer. You cannot
out-price free in this audience.
**What the niche DOES pay for:** hosted convenience (Healthchecks.io,
BorgBase), storage, and accumulated data/intelligence no individual can
self-build. argus' hosted version sells exactly that (+ off-site vantage
point, which self-hosting your own backup monitor structurally can't give).

---

*Template for future entries:*

## F-XXX — <title>
**Tried:** <what>
**Why it failed:** <evidence>
**Lesson:** <transferable rule>
