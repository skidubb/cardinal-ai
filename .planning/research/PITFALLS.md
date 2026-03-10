# Pitfalls Research: CE-AGENTS Full-Stack Integration

**Domain:** Wiring FastAPI + React + PostgreSQL into deployable multi-agent AI platform
**Researched:** 2026-03-10
**Confidence:** HIGH (based on codebase analysis of actual runner.py, server.py, and protocol code)

---

## Critical Pitfalls

### C-1: SSE Proxy Buffering Kills Streaming in Production

**The problem:** Nginx, Cloudflare, and most reverse proxies buffer responses by default. SSE events queue up and deliver as a batch when the buffer fills or the connection closes — making "live progress" feel like "silence then dump."

**Warning signs:** Streaming works perfectly on localhost, breaks silently behind any proxy.

**Prevention:**
- Add `X-Accel-Buffering: no` header to all SSE responses
- Configure Nginx: `proxy_buffering off; proxy_cache off;` for `/api/runs/*/stream`
- Test through the actual production proxy before declaring done

**Phase:** API endpoints wiring (must be baked into SSE response headers from the start)

---

### C-2: Silent Production Agent Mode Fallback

**The problem:** `api/runner.py` currently builds dict agents, not SdkAgents. The `agent_provider.py` import chain (`sys.path.insert` → import SdkAgent) is fragile. Spaces in `CE - Agent Builder/` directory name make Docker COPY paths break silently. If production mode fails to import, it falls back to research mode without warning — producing inferior output that Scott delivers to clients.

**Warning signs:** Protocol runs complete successfully but output quality is noticeably worse. No error, no warning.

**Prevention:**
- Add startup assertion: verify SdkAgent import succeeds before accepting API requests
- Log agent mode prominently at run start ("Running in PRODUCTION mode with 3 SdkAgents")
- In Docker, use JSON array form for COPY: `COPY ["CE - Agent Builder/", "/app/agent-builder/"]`
- Never silently fall back to research mode in production — fail loudly

**Phase:** API endpoints wiring + Docker/deployment

---

### C-3: CORS Whitelist Hardcoded to Localhost

**The problem:** `server.py` has `allow_origins=["http://localhost:5173", "http://localhost:5174"]`. Deployed frontend URL won't match. Using `allow_origins=["*"]` with `allow_credentials=True` is mutually exclusive per CORS spec — browsers will reject it.

**Warning signs:** UI works locally, gets CORS errors in production. Auth cookies don't send.

**Prevention:**
- Load allowed origins from env var: `CORS_ORIGINS=https://ce-agents.up.railway.app`
- Never use `*` with credentials
- Test CORS with actual deployed frontend URL before declaring deployment done

**Phase:** Cloud deployment

---

### C-4: DB Connection Pool Exhaustion Under Concurrent Runs

**The problem:** `runner.py` uses synchronous SQLModel sessions inside async SSE generators. Multiple concurrent protocol runs (each with long-running DB connections for persistence) will exhaust the connection pool.

**Warning signs:** Second run hangs or times out while first is still streaming. Works fine with single runs.

**Prevention:**
- Use async sessions (`AsyncSession`) consistently in the API layer
- Set explicit pool size limits matching expected concurrency: `pool_size=5, max_overflow=10`
- Use short-lived sessions (open/close per operation), not session-per-request for SSE generators
- Add connection pool metrics to health endpoint

**Phase:** API endpoints wiring

---

### C-5: Docker COPY with Spaces in Directory Names

**The problem:** `COPY CE - Agent Builder/ /app/agent-builder/` silently copies nothing. Docker's standard COPY syntax treats spaces as argument separators.

**Warning signs:** Docker build succeeds. Import fails at runtime with `ModuleNotFoundError`.

**Prevention:**
- Always use JSON array form: `COPY ["CE - Agent Builder/", "/app/agent-builder/"]`
- Verify in CI: add a Docker build step that asserts the copied directories exist
- Long-term: consider renaming directories to remove spaces

**Phase:** Docker/deployment

---

## Moderate Pitfalls

### M-1: Client Disconnect Doesn't Cancel Orchestrator Task

**The problem:** When the SSE client disconnects (user navigates away), `asyncio.create_task()` keeps running the orchestrator. API credits continue burning for a run nobody is watching.

**Prevention:**
- Use `asyncio.shield()` selectively, cancel task on client disconnect
- Check `request.is_disconnected()` in the SSE generator loop
- Log cancelled runs with partial cost

**Phase:** API endpoints wiring

---

### M-2: Global Cost Tracker / Event Queue Breaks Under Concurrency

**The problem:** `protocols/llm.py` uses `contextvars.ContextVar` for `_cost_tracker` and `_event_queue` — this is correct. But verify that `set_cost_tracker()` and `set_event_queue()` are called inside the async task context, not in the request handler (which would set the var in the wrong context).

**Warning signs:** Two concurrent runs show mixed cost data or events from wrong run.

**Prevention:**
- Set context vars inside the `asyncio.create_task()` coroutine, not in the endpoint handler
- Add run_id to all SSE events for client-side filtering
- Test with 2 concurrent runs explicitly

**Phase:** API endpoints wiring

---

### M-3: EventSource Doesn't Support Custom Auth Headers

**The problem:** Browser's native `EventSource` API cannot send `Authorization: Bearer <token>` headers. The current `X-API-Key` auth middleware blocks SSE connections from authenticated browsers.

**Prevention:**
- Use `@microsoft/fetch-event-source` (supports custom headers and POST)
- OR issue a short-lived session cookie after JWT verification, check cookie on SSE endpoints
- Don't rely on query-param tokens (appears in logs and browser history)

**Phase:** Auth implementation

---

### M-4: WeasyPrint System Dependencies in Docker

**The problem:** WeasyPrint needs `libpango-1.0-0`, `libharfbuzz0b`, `libffi-dev`, `libgdk-pixbuf-2.0-0` — not present in `python:3.13-slim`.

**Prevention:**
- Add `apt-get install` in Dockerfile for these packages
- Pin package versions for reproducible builds
- Test PDF generation inside the Docker container, not just locally

**Phase:** Report/PDF generation + Docker

---

### M-5: Cloud Free-Tier Sleep Kills Long Protocol Runs

**The problem:** Free tiers on Render, Railway, etc. sleep after inactivity. A 2-minute protocol run that starts after 14 minutes of inactivity may be killed mid-execution.

**Prevention:**
- Use paid tier (Railway Hobby at $5/mo is sufficient)
- Configure minimum instance count = 1
- Set appropriate request timeout (120s+) for protocol execution endpoints

**Phase:** Cloud deployment

---

### M-6: Alembic Migration State Drift Between Local and Cloud

**The problem:** Local Postgres and cloud Postgres may have different migration states. Running `alembic upgrade head` on cloud without checking current state can fail or produce schema conflicts.

**Prevention:**
- Always run `alembic current` before `alembic upgrade head`
- Include migration check in deployment script
- Use a single migration flow (not separate local/cloud migration paths)

**Phase:** Cloud deployment

---

## Prevention Checklist by Phase

| Phase | Pitfalls to Address |
|-------|-------------------|
| API endpoints wiring | C-1 (SSE buffering headers), C-2 (agent mode assertion), C-4 (async sessions), M-1 (task cancellation), M-2 (context vars in task) |
| Auth implementation | M-3 (EventSource auth), C-3 (CORS origins from env) |
| Report/PDF generation | M-4 (WeasyPrint system deps) |
| Docker/deployment | C-5 (COPY with spaces), C-2 (SdkAgent import in container), C-3 (CORS whitelist), M-5 (free-tier sleep), M-6 (migration state) |

---
*Pitfalls research for: CE-AGENTS full-stack integration*
*Researched: 2026-03-10*
