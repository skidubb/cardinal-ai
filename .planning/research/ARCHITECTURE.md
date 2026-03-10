# Architecture Research: CE-AGENTS Full-Stack Integration

**Domain:** Wiring FastAPI + React + PostgreSQL into deployable multi-agent AI platform
**Researched:** 2026-03-10
**Confidence:** HIGH — all findings based on direct codebase inspection

---

## Current Architecture (What Exists)

```
                    +-------------------+
                    |   React UI        |  ← Pages exist, not wired
                    | (Vite + TypeScript)|
                    +--------+----------+
                             | (no connection)
                    +--------v----------+
                    |   FastAPI Server   |  ← Routers exist as stubs
                    |  (api/server.py)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+        +----------v---------+
    | Protocol           |        |  Evaluation        |
    | Orchestrators      |        |  (CE - Evals)      |
    | (52 protocols)     |        |  (separate workflow)|
    +--------+-----------+        +--------------------+
             |
    +--------v-----------+
    | Agent Layer         |
    | (SdkAgent + tools)  |
    +--------+------------+
             |
    +--------v-------------------------------+
    |     ce-db (PostgreSQL + Alembic)        |
    +----------------------------------------+
```

### What Already Works

| Component | Status | Key Files |
|-----------|--------|-----------|
| SSE streaming infrastructure | **Complete** | `api/runner.py` (event queue + async generator), `api/routers/runs.py` (EventSourceResponse), `ui/src/hooks/useRunStream.ts` |
| Protocol discovery | **Complete** | `api/runner.py` dynamically scans `protocols/p*/orchestrator.py` |
| Agent resolution | **Partial** | `agent_provider.py` builds SdkAgents but uses fragile `sys.path.insert` |
| Pipeline/chain execution | **Complete** | `api/runner.py` chains protocols sequentially, passes `{prev_output}` forward |
| Zustand stores | **Complete** | `ui/src/stores/` — protocol, run, agent, team, pipeline stores with API fetch hooks |
| Quality scoring | **Complete** | `api/runner.py` runs QualityJudge after each protocol, persists scores |

### What's Missing (The Gaps)

| Gap | Impact | Details |
|-----|--------|---------|
| Router endpoints are stubs | UI can't load data | `routers/protocols.py`, `agents.py`, `runs.py`, `pipelines.py` — all have empty or minimal handlers |
| No auth middleware | Can't deploy publicly | `server.py` has `X-API-Key` check but no user auth |
| Agent path is fragile | Production mode fails silently in Docker | `sys.path.insert(0, "CE - Agent Builder/src")` breaks with relative paths |
| CORS hardcoded to localhost | Blocks cloud deployment | Only `localhost:5173` and `localhost:5174` allowed |
| No ProtocolReport format | Raw JSON output, not executive-readable | Each protocol has its own result dataclass; no shared presentation layer |
| No PDF/export | Can't deliver client artifacts | No export infrastructure exists |
| SQLite for some data | Lost on container restart | Agent, Team, Pipeline records in SQLite need persistent volume or Postgres migration |

---

## Target Architecture

```
                    +-------------------+
                    |   React UI        |  ← Served as static files by FastAPI
                    | (built → /static) |     (same origin = no CORS issues)
                    +--------+----------+
                             | REST + SSE (same origin)
                    +--------v----------+
                    |   FastAPI Server   |  ← JWT auth middleware
                    |  + StaticFiles    |     All endpoints implemented
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v----+  +------v------+  +----v--------+
    | Protocol     |  | Report      |  | Auth        |
    | Execution    |  | Generation  |  | (JWT +      |
    | (orchestrate)|  | (WeasyPrint)|  |  cookies)   |
    +--------+-----+  +------+------+  +-------------+
             |               |
    +--------v-----------+   |
    | Agent Layer         |  |
    | (SdkAgent, prod mode)|  |
    +--------+------------+   |
             |               |
    +--------v---------------v-----------+
    |     PostgreSQL (all data)           |
    |  Runs | Agents | Users | Reports   |
    +------------------------------------+
```

### Key Architecture Decisions

#### 1. Serve React SPA from FastAPI StaticFiles

**Why:** Same origin eliminates CORS entirely. Auth middleware applies uniformly. Single URL for client sharing. Single container for deployment.

**How:** Build React app → `dist/` → FastAPI `StaticFiles` mount at `/`. API routes at `/api/`. Catch-all route returns `index.html` for client-side routing.

#### 2. Single Uvicorn Worker (Required)

**Why:** The `asyncio.Queue` used for SSE tool events in `api/runner.py` is in-process memory. Multi-worker deployments silently drop events between workers.

**Implication:** Sufficient for Scott's use case (single-user, 1-2 concurrent runs). If scaling needed later, switch to Redis pub/sub for cross-worker SSE.

#### 3. Production Agent Mode with Absolute Path

**Why:** Current `sys.path.insert(0, "CE - Agent Builder/src")` breaks in Docker. Must use absolute path resolved from a known anchor (env var or package install).

**How:** Set `AGENT_BUILDER_SRC` env var in Docker, resolve in `agent_provider.py`. Assert on startup.

#### 4. All Data in PostgreSQL

**Why:** SQLite records (agents, teams, pipelines) are lost on container restart. PostgreSQL already runs for runs/evals.

**How:** Migrate SQLite-backed stores to ce-db models. Seed default agents on first startup from `protocols/agents.py` registry.

---

## Component Boundaries

### API Layer (`api/`)

| Router | Responsibility | Data Source |
|--------|---------------|-------------|
| `protocols.py` | List protocols, execute runs, get protocol metadata | Protocol discovery (filesystem scan) |
| `runs.py` | Run history, SSE streaming, run details | PostgreSQL `runs` table |
| `agents.py` | Agent registry, agent details | PostgreSQL `agents` table (seeded from registry) |
| `pipelines.py` | Protocol chain CRUD, execute chains | PostgreSQL `pipelines` table |
| `teams.py` | Agent team presets | PostgreSQL `teams` table |
| `auth.py` | Login, token refresh, current user | PostgreSQL `users` table |
| `reports.py` | PDF/HTML export for a run | PostgreSQL `runs` table → WeasyPrint |

### Data Flow: Protocol Execution

```
UI: POST /api/protocols/run {protocol, question, agents}
  │
  ├─► Auth middleware validates JWT
  │
  ├─► Runner resolves orchestrator class (filesystem discovery)
  ├─► Runner builds agents (production mode via AgentBridge)
  ├─► Runner creates asyncio.Task for orchestrator.run()
  │     │
  │     ├─► Set contextvars (cost_tracker, event_queue) INSIDE task
  │     ├─► Orchestrator runs stages (parallel agent calls, synthesis)
  │     ├─► Events pushed to asyncio.Queue (stage_start, stage_complete, tool_call)
  │     └─► Result persisted to PostgreSQL, Langfuse trace scored
  │
  └─► SSE endpoint: GET /api/runs/{id}/stream
        ├─► Auth check (cookie or bearer token)
        ├─► Drain asyncio.Queue → yield SSE events
        ├─► On client disconnect → cancel orchestrator task
        └─► Final event: run_complete with result summary
```

### Data Flow: Report Export

```
UI: GET /api/reports/{run_id}/pdf
  │
  ├─► Load Run from PostgreSQL (result_json, cost, agent_outputs)
  ├─► Transform to ProtocolReport dataclass
  ├─► Render Jinja2 HTML template with ProtocolReport fields
  ├─► WeasyPrint converts HTML → PDF bytes
  └─► Return StreamingResponse with Content-Disposition: attachment
```

---

## Suggested Build Order

Build order follows dependency chain — each layer unblocks the next.

### Layer 1: Fix Agent Provider + Startup Assertions
- Fix `agent_provider.py` to use absolute path (env var `AGENT_BUILDER_SRC`)
- Add startup check: assert SdkAgent import succeeds
- Log agent mode at API startup

### Layer 2: Wire API Endpoints
- Fill router stubs: protocols list, agents list, runs list, run details
- Wire `POST /api/protocols/run` to `api/runner.py`
- Wire `GET /api/runs/{id}/stream` SSE endpoint
- Add `X-Accel-Buffering: no` header to SSE responses
- Set contextvars inside asyncio task (not request handler)

### Layer 3: ProtocolReport + Structured Output
- Define shared `ProtocolReport` dataclass (participants, findings, disagreements, confidence, synthesis, agent_contributions)
- Transform protocol result dataclasses to ProtocolReport
- UI components to render ProtocolReport sections

### Layer 4: Auth + Frontend Wiring
- Add `users` table (Alembic migration)
- JWT auth endpoints (login, refresh)
- React auth context + protected routes
- Cookie-based auth for SSE endpoints
- CORS origins from env var

### Layer 5: Report Export
- Jinja2 HTML report template (mirrors browser ProtocolReport view)
- WeasyPrint PDF endpoint
- Download button in run view

### Layer 6: Docker + Cloud Deployment
- Multi-stage Dockerfile (Python backend + React static build + Nginx)
- Extend docker-compose for full local stack
- Railway deployment config
- Makefile for one-command startup
- End-to-end smoke test

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| SdkAgent import fails silently in Docker | Critical | Startup assertion + explicit error |
| SSE buffering in production proxy | Critical | `X-Accel-Buffering: no` header |
| CORS blocks cloud frontend | High | Origins from env var, test before declaring done |
| WeasyPrint system deps missing in Docker | Medium | `apt-get install` in Dockerfile, test PDF in container |
| Concurrent runs corrupt context vars | Medium | Set vars inside asyncio task, not handler |
| Long runs killed by platform timeout | Medium | Set 120s+ request timeout, Railway paid tier |

---
*Architecture research for: CE-AGENTS full-stack integration*
*Researched: 2026-03-10*
