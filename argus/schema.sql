-- schema.sql — argus — SQLite schema v1
--
-- Two tables only (MVP, D-002): jobs and their ping history. Single-writer,
-- trivial write volume (even 100 jobs hourly is nothing), RPi-friendly.
--
-- Time is stored as ISO-8601 UTC strings written by Python (not SQL defaults)
-- so tests can inject a fixed clock. created_at is the one exception (display
-- only, never used for alerting math).

PRAGMA foreign_keys = ON;

-- A monitored backup job. The dead-man's switch lives here: silence past
-- next-expected-run + grace = LATE. `token` is the per-job ingest secret
-- (Healthchecks-style, in the URL path).
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    token         TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,

    -- Schedule: 'interval' (schedule_expr = seconds) or 'cron' (5-field expr).
    schedule_kind TEXT    NOT NULL CHECK (schedule_kind IN ('interval', 'cron')),
    schedule_expr TEXT    NOT NULL,
    grace_seconds INTEGER NOT NULL DEFAULT 3600 CHECK (grace_seconds >= 0),

    paused        INTEGER NOT NULL DEFAULT 0,

    -- Derived, recomputed on every ping and every sweep.
    state         TEXT    NOT NULL DEFAULT 'new'
                  CHECK (state IN ('new', 'up', 'late', 'failed')),
    -- Last state we actually fired an alert for, for de-duplication: we alert
    -- on the TRANSITION into late/failed, not every sweep. NULL = nothing
    -- outstanding (also reset on recovery).
    alerted_state TEXT,
    -- Same idea for the warn-level size/duration anomaly: 1 once we've alerted
    -- on an anomalous backup, cleared when a later backup looks normal again.
    -- Separate axis from `state` (a job can be 'up' yet anomalous).
    anomaly_alerted INTEGER NOT NULL DEFAULT 0,

    last_ping_at  TEXT,   -- ISO-8601 UTC of the most recent ping, NULL if never

    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- One row per received ping. Feeds the size/duration history (anomaly check)
-- and the dashboard sparkline.
CREATE TABLE IF NOT EXISTS pings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    received_at TEXT    NOT NULL,   -- ISO-8601 UTC
    flavor      TEXT    NOT NULL DEFAULT 'generic',
    status      TEXT    NOT NULL CHECK (status IN ('success', 'fail')),
    exit_code   INTEGER,
    bytes       INTEGER,            -- size of this backup, if the flavor reports it
    duration_s  REAL,
    log_tail    TEXT
);

CREATE INDEX IF NOT EXISTS idx_pings_job ON pings(job_id, received_at);
