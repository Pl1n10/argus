"""FastAPI app: job API + public ingest + server-rendered dashboard.

create_app takes an already-built Store and channel list (so tests inject an
in-memory DB and a recording channel — no network, no real scheduler). The CLI
entrypoint (__main__.py) builds the real ones and starts the APScheduler sweep.

Auth (D: single-user MVP): one admin token guards the dashboard and the job
API. The ingest endpoint is intentionally open — the per-job secret token in
the URL path IS its auth (D-001). /health is open for container probes.
"""
from __future__ import annotations

import secrets
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from argus import ingest as ingest_mod
from argus import monitor
from argus.alerts import Channel
from argus.checks import duration_anomaly, size_anomaly
from argus.clock import utcnow
from argus.db import JobNotFound, Store
from argus.scheduling import ScheduleError, validate

_TEMPLATES = Path(__file__).resolve().parent / "templates"
# Dashboard auto-refresh cadence — matches the sweep interval so the board
# reflects state roughly as fast as the dead-man's switch updates it.
_DASHBOARD_REFRESH_SECONDS = 60
# Hard cap on an ingest request body (the endpoint is open — token is its auth).
_MAX_INGEST_BODY = 64 * 1024


def create_app(
    store: Store,
    channels: list[Channel] | None = None,
    *,
    base_url: str = "http://localhost:8000",
    admin_token: str | None = None,
) -> FastAPI:
    channels = channels or []
    base_url = base_url.rstrip("/")
    app = FastAPI(title="argus", docs_url=None, redoc_url=None)
    jinja = Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )

    # ─────────────────────────────── auth ───────────────────────────────
    def check_admin(request: Request) -> None:
        """Allow if no admin_token configured (dev), else require it via Bearer
        header, ?token=, or the argus_token cookie."""
        if admin_token is None:
            return
        header = request.headers.get("authorization", "")
        token = header[7:] if header.lower().startswith("bearer ") else None
        token = token or request.query_params.get("token") or request.cookies.get("argus_token")
        # Constant-time compare so the token can't be recovered by timing.
        if token is None or not secrets.compare_digest(token, admin_token):
            raise HTTPException(status_code=401, detail="admin token required")

    def ingest_url(token: str) -> str:
        return f"{base_url}/ingest/{token}"

    def job_public(job: dict) -> dict:
        return {
            "id": job["id"],
            "name": job["name"],
            "schedule_kind": job["schedule_kind"],
            "schedule_expr": job["schedule_expr"],
            "grace_seconds": job["grace_seconds"],
            "state": job["state"],
            "paused": bool(job["paused"]),
            "last_ping_at": job["last_ping_at"],
            "ingest_url": ingest_url(job["token"]),
        }

    # ─────────────────────────────── health ─────────────────────────────
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # ──────────────────────────────── API ───────────────────────────────
    @app.post("/api/jobs", status_code=201)
    async def create_job(request: Request, _: None = Depends(check_admin)) -> JSONResponse:
        data = await request.json()
        name = (data.get("name") or "").strip()
        kind = data.get("schedule_kind", "interval")
        expr = str(data.get("schedule_expr", ""))
        grace = int(data.get("grace_seconds", 3600))
        if not name:
            raise HTTPException(400, "name is required")
        try:
            validate(kind, expr)
        except ScheduleError as e:
            raise HTTPException(400, str(e)) from e
        job = store.create_job(name=name, schedule_kind=kind,
                               schedule_expr=expr, grace_seconds=grace)
        return JSONResponse(job_public(job), status_code=201)

    @app.get("/api/jobs")
    def list_jobs(_: None = Depends(check_admin)) -> list[dict]:
        return [job_public(j) for j in store.list_jobs()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: int, _: None = Depends(check_admin)) -> dict:
        try:
            return job_public(store.get_job(job_id))
        except JobNotFound:
            raise HTTPException(404, "job not found") from None

    @app.delete("/api/jobs/{job_id}", status_code=204)
    def delete_job(job_id: int, _: None = Depends(check_admin)) -> None:
        try:
            store.delete_job(job_id)
        except JobNotFound:
            raise HTTPException(404, "job not found") from None

    @app.post("/api/jobs/{job_id}/pause")
    def pause_job(job_id: int, _: None = Depends(check_admin)) -> dict:
        try:
            return job_public(store.set_paused(job_id, True))
        except JobNotFound:
            raise HTTPException(404, "job not found") from None

    @app.post("/api/jobs/{job_id}/unpause")
    def unpause_job(job_id: int, _: None = Depends(check_admin)) -> dict:
        try:
            return job_public(store.set_paused(job_id, False))
        except JobNotFound:
            raise HTTPException(404, "job not found") from None

    # ─────────────────────────────── ingest ─────────────────────────────
    @app.api_route("/ingest/{token}", methods=["GET", "POST"])
    async def ingest(token: str, request: Request) -> dict:
        job = store.get_job_by_token(token)
        if job is None:
            raise HTTPException(404, "unknown ingest token")
        flavor = request.query_params.get("flavor", "generic")
        body: dict = {}
        if request.method == "POST":
            # Open endpoint: cap the body so a runaway/hostile job with a valid
            # token can't fill the disk. log_tail is also truncated downstream.
            # Known gap (D-011): a chunked request with no Content-Length slips
            # past this; log_tail truncation still bounds what hits SQLite.
            clen = request.headers.get("content-length")
            if clen is not None and clen.isdigit() and int(clen) > _MAX_INGEST_BODY:
                raise HTTPException(413, "ingest body too large")
            try:
                parsed = await request.json()
                if isinstance(parsed, dict):
                    body = parsed
            except Exception:
                body = {}
        # Shell-friendly: `curl "$URL?exit_code=$?"` with no body at all.
        if flavor == "generic" and "exit_code" in request.query_params:
            body.setdefault("exit_code", request.query_params["exit_code"])
        try:
            ping = ingest_mod.parse(flavor, body)
        except ingest_mod.ParseError as e:
            raise HTTPException(400, str(e)) from e
        fresh = store.record_ping(job["id"], ping)
        monitor.evaluate_job(store, fresh, channels)
        updated = store.get_job(job["id"])  # evaluate_job persisted the new state
        return {"ok": True, "job": updated["name"], "status": ping.status,
                "state": updated["state"]}

    # ───────────────────────────── dashboard ────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, _: None = Depends(check_admin)) -> HTMLResponse:
        jobs = []
        for j in store.list_jobs():
            sizes = store.recent_sizes(j["id"], 10)
            durations = store.recent_durations(j["id"], 10)
            jobs.append({
                **job_public(j),
                "last_bytes": j.get("last_bytes"),
                "sparkline": _sparkline(sizes),
                "size_anomaly": size_anomaly(sizes[:-1], sizes[-1]) if sizes else False,
                "duration_anomaly": (
                    duration_anomaly(durations[:-1], durations[-1]) if durations else False
                ),
            })
        html = jinja.get_template("dashboard.html").render(
            jobs=jobs, base_url=base_url,
            updated_at=utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            refresh_seconds=_DASHBOARD_REFRESH_SECONDS,
        )
        resp = HTMLResponse(html)
        # If the admin authenticated via ?token=, remember it so links work.
        if admin_token and request.query_params.get("token") == admin_token:
            resp.set_cookie("argus_token", admin_token, httponly=True, samesite="lax")
        return resp

    return app


def _sparkline(sizes: list[int], width: int = 90, height: int = 20) -> str:
    """A tiny inline-SVG sparkline of recent backup sizes (no JS, no deps)."""
    if len(sizes) < 2:
        return ""
    lo, hi = min(sizes), max(sizes)
    span = (hi - lo) or 1
    n = len(sizes)
    pts = []
    for i, v in enumerate(sizes):
        x = round(i / (n - 1) * width, 1)
        y = round(height - (v - lo) / span * height, 1)
        pts.append(f"{x},{y}")
    poly = " ".join(pts)
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="none" class="spark"><polyline points="{poly}" '
            f'fill="none" stroke="currentColor" stroke-width="1.5"/></svg>')


def build_alert_client() -> httpx.Client:
    """Shared httpx client for real alert channels (CLI path)."""
    return httpx.Client()
