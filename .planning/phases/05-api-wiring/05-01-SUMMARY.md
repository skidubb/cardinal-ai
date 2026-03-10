---
phase: 05-api-wiring
plan: 01
subsystem: api
tags: [fastapi, sse, sqlmodel, sqlite, httpx, pytest]

requires:
  - phase: 04-agent-provider
    provides: production agent mode wired into runner.py

provides:
  - POST /api/protocols/run at canonical URL with X-Accel-Buffering header
  - POST /api/pipelines/run at canonical URL with X-Accel-Buffering header
  - GET /api/runs/{id}/stream for completed-run replay as SSE
  - trace_id field in Run model and GET /api/runs/{id} response
  - TestClient test infrastructure with in-memory SQLite fixture

affects:
  - 05-02 (downstream API wiring plans)
  - 06-ui (frontend consumes these SSE endpoints)
  - 07-export (uses run data including trace_id)

tech-stack:
  added: []
  patterns:
    - POST /run declared before GET /{key}/stages in protocols.py to prevent route shadowing
    - GET /{run_id}/stream declared before GET /{run_id} in runs.py to prevent route shadowing
    - EventSourceResponse always constructed with headers={"X-Accel-Buffering": "no"}
    - conftest.py overrides engine + get_session dependency and patches lifespan for TestClient isolation

key-files:
  created:
    - CE - Multi-Agent Orchestration/tests/conftest.py
    - CE - Multi-Agent Orchestration/tests/test_api_endpoints.py
  modified:
    - CE - Multi-Agent Orchestration/api/models.py
    - CE - Multi-Agent Orchestration/api/routers/protocols.py
    - CE - Multi-Agent Orchestration/api/routers/pipelines.py
    - CE - Multi-Agent Orchestration/api/routers/runs.py
    - CE - Multi-Agent Orchestration/api/runner.py

key-decisions:
  - "POST /api/runs/protocol and POST /api/runs/pipeline removed; replaced by POST /api/protocols/run and POST /api/pipelines/run"
  - "ProtocolRunRequest and PipelineRunRequest kept in runs.py for backward-compat; protocols.py and pipelines.py import them from there"
  - "Old route 405 (method not allowed) is an acceptable signal that POST endpoint is gone — tests accept 404 or 405"
  - "Stream replay queries AgentOutput table; synthesis row keyed by agent_key='_synthesis'"

patterns-established:
  - "Route ordering: POST /run before GET /{key} parameter routes to prevent FastAPI path parameter capture"
  - "TestClient isolation: patch lifespan + override engine + override get_session dependency"
  - "SSE anti-buffering: all EventSourceResponse include headers={'X-Accel-Buffering': 'no'}"

requirements-completed: [API-01, API-02, API-03, API-04, API-05, API-06, API-07]

duration: 8min
completed: 2026-03-10
---

# Phase 05 Plan 01: API Wiring — Canonical URLs, SSE Headers, trace_id, Stream Replay

**Canonical SSE endpoints at POST /api/protocols/run and POST /api/pipelines/run with X-Accel-Buffering header, trace_id in Run model, GET /{id}/stream replay, and 17-test TestClient suite**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-10T19:18:28Z
- **Completed:** 2026-03-10T19:26:43Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Moved run initiation to canonical URLs (POST /api/protocols/run, POST /api/pipelines/run) with X-Accel-Buffering: no on all SSE responses
- Added trace_id column to Run model and persist envelope.trace_id on completion; included in GET /api/runs/{id} and list responses
- Added GET /api/runs/{id}/stream that replays a completed run's agent outputs and synthesis as SSE events
- Created 17-test TestClient suite covering health, list endpoints, SSE content-type/headers, stream replay, trace_id, and old-route removal

## Task Commits

1. **Task 1: Test infrastructure and endpoint tests** - `f961211` (test)
2. **Task 2: Canonical URLs, SSE headers, trace_id, stream replay** - `9fc1942` (feat)

## Files Created/Modified

- `CE - Multi-Agent Orchestration/tests/conftest.py` - In-memory SQLite engine fixture, no-op lifespan patch, TestClient factory
- `CE - Multi-Agent Orchestration/tests/test_api_endpoints.py` - 17 endpoint tests (health, lists, SSE, stream, trace_id)
- `CE - Multi-Agent Orchestration/api/models.py` - Added trace_id: Optional[str] to Run model
- `CE - Multi-Agent Orchestration/api/routers/protocols.py` - Added POST /run handler before GET /{key}/stages
- `CE - Multi-Agent Orchestration/api/routers/pipelines.py` - Added POST /run handler before GET list
- `CE - Multi-Agent Orchestration/api/routers/runs.py` - Removed POST /protocol and /pipeline; added GET /{id}/stream replay; added trace_id to responses
- `CE - Multi-Agent Orchestration/api/runner.py` - Set run.trace_id = envelope.trace_id in persist block

## Decisions Made

- Kept `ProtocolRunRequest` and `PipelineRunRequest` in `runs.py` for backward compatibility with `test_runs_api.py` — protocols.py and pipelines.py import from there
- Old routes return 405 Method Not Allowed (FastAPI matches path for GET but not POST) — treated as equivalent to 404 in tests, both signal the POST endpoint is gone
- Stream replay reads from `AgentOutput` table using agent_key convention: regular agents by key, synthesis row by `_synthesis`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all 181 tests pass including 17 new ones.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All canonical API routes are in place and tested
- trace_id flows from Langfuse through runner → Run model → GET responses
- TestClient infrastructure ready for 05-02 tests
- Ready for 05-02 (agents endpoint, integrations, teams CRUD if planned)

---
*Phase: 05-api-wiring*
*Completed: 2026-03-10*
