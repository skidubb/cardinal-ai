# Phase 5: API Wiring - Research

**Researched:** 2026-03-10
**Domain:** FastAPI + SSE streaming + asyncio task lifecycle + ContextVar isolation
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| API-01 | POST /api/protocols/run — accepts protocol key, question, agent list; executes orchestrator; returns run ID | URL is wrong: endpoint exists at POST /api/runs/protocol; needs rename to /api/protocols/run |
| API-02 | GET /api/runs/{id}/stream — SSE events with X-Accel-Buffering: no header | Stream is embedded in the POST response; needs separate GET /stream path + header |
| API-03 | GET /api/protocols — list all protocols with name, description, category, stage metadata | Fully implemented in api/routers/protocols.py |
| API-04 | GET /api/agents — agent registry with @group expansion | Fully implemented in api/routers/agents.py |
| API-05 | GET /api/runs — paginated run history with cost, status, timestamp | Implemented with limit/offset pagination |
| API-06 | GET /api/runs/{id} — full run detail with agent outputs, cost breakdown, trace link | Implemented; missing Langfuse trace link in response |
| API-07 | POST /api/pipelines/run — execute protocol chain with context chaining | URL is wrong: endpoint exists at POST /api/runs/pipeline; needs rename |
| API-08 | GET /api/pipelines — available pipeline presets (curated chains) | Lists DB pipelines but has no hardcoded preset library |
| API-09 | Context vars set inside asyncio task, not request handler | BUG: cost_tracker and event_queue are set in the generator (request context) before asyncio.create_task; task inherits the snapshot but the generator continues to mutate the same ContextVar — needs copy_context() |
| API-10 | Client disconnect cancels orchestrator asyncio task | NOT implemented; sse_starlette sends disconnect but runner.py has no cancel logic |
</phase_requirements>

---

## Summary

Phase 5 is overwhelmingly a **gap-closing and bug-fixing phase**, not a greenfield build. The FastAPI server, SSE streaming infrastructure, SQLModel database, all major routers, and the runner are already written and functional. The implementation gaps fall into three categories:

**URL mismatches (2 endpoints):** The spec requires POST /api/protocols/run and POST /api/pipelines/run. The existing code routes these through POST /api/runs/protocol and POST /api/runs/pipeline. The fix is either to add aliases in the existing router or move the handlers. Because GET /api/runs/{id} must coexist in the same router, the cleanest solution is keeping the runs router for read operations and adding /run sub-endpoints to the protocols and pipelines routers.

**Missing response details and headers (2 gaps):** API-02 requires a separate GET /api/runs/{id}/stream endpoint and the X-Accel-Buffering: no header on SSE responses. API-06 needs the Langfuse trace link in the run detail response (already stored in Postgres via persist_run but not returned by GET /api/runs/{id}).

**Critical runtime bugs (2 gaps):** API-09 is a subtle but serious correctness bug — context vars (cost_tracker, event_queue) are set in the async generator body before asyncio.create_task(), which means the task inherits those values, but the real problem is that set_cost_tracker(None) at the end of one run affects concurrent runs sharing the same event loop context. The fix is to use `copy_context().run()` or set vars inside the task itself. API-10 (disconnect cancellation) is the highest-value missing feature — without it, a closed browser tab continues burning API credits.

**Primary recommendation:** Address all 10 requirements in 2 focused plans: Plan 05-01 handles the URL routing + SSE stream endpoint + X-Accel-Buffering + Langfuse trace link. Plan 05-02 handles context var isolation (copy_context) + client disconnect cancellation + pipeline presets.

---

## Standard Stack

### Core (already in requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.104.0 | HTTP framework, routing, dependency injection | Already used throughout |
| sse-starlette | >=1.8.0 | EventSourceResponse with proper SSE framing | Already used for streaming |
| sqlmodel | >=0.0.14 | SQLite ORM (Run, AgentOutput models) | Already used |
| uvicorn[standard] | >=0.24.0 | ASGI server | Already used |
| pydantic | >=2.0.0 | Request/response schema validation | Already used |

### No new dependencies needed
All libraries required for Phase 5 are already installed. The work is purely in Python logic using stdlib `asyncio`, `contextvars`, and `copy_context()`.

---

## Architecture Patterns

### Recommended URL Structure After Phase 5

```
POST   /api/protocols/run          → start a single protocol run (SSE response)
GET    /api/runs/{id}/stream       → stream SSE events for an existing run
GET    /api/protocols              → list protocols (existing, works)
GET    /api/agents                 → list agents (existing, works)
GET    /api/runs                   → paginated run history (existing, works)
GET    /api/runs/{id}              → run detail with trace link (extend existing)
POST   /api/pipelines/run          → start pipeline chain run (SSE response)
GET    /api/pipelines              → list pipeline presets (extend existing)
```

### Pattern 1: POST /api/protocols/run (API-01)

**What:** Move the SSE-streaming POST handler from `api/routers/runs.py` into `api/routers/protocols.py` as `POST /api/protocols/run`. The existing POST /api/runs/protocol can be kept as a deprecated alias or removed.

**Why:** The requirement specifies this URL. The router that owns protocol metadata (protocols.py) should also own the run-initiation endpoint. The runs router should remain purely for reading run history and streaming.

```python
# api/routers/protocols.py — add this handler
@router.post("/run")
async def start_protocol_run(payload: ProtocolRunRequest) -> EventSourceResponse:
    with Session(engine) as session:
        run = Run(type="protocol", protocol_key=payload.protocol_key,
                  question=payload.question, status="pending")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    return EventSourceResponse(
        run_protocol_stream(...),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},  # API-02 header
    )
```

### Pattern 2: GET /api/runs/{id}/stream (API-02)

**What:** Add a separate GET endpoint for streaming an in-progress run. The current architecture creates the run record and immediately starts streaming in one POST call. To support a separate /stream endpoint, the run must be created first (POST returns run_id), then the client connects to GET /api/runs/{id}/stream.

**Architecture decision:** Two valid approaches exist:

Option A (two-step): POST /api/protocols/run creates the run record, stores the orchestrator task in a module-level dict, returns `{"run_id": N}` as JSON (not SSE). GET /api/runs/{id}/stream then connects to stream from the in-flight task. This cleanly separates run creation from streaming and enables reconnection.

Option B (one-step SSE with run_start event): POST /api/protocols/run returns an EventSourceResponse immediately; the first event is `run_start` with the run_id. The UI subscribes to the POST SSE directly. GET /api/runs/{id}/stream is only needed for reconnection.

**Recommendation: Option B** for Phase 5. It matches the existing runner.py pattern (which already yields `run_start` as the first event). The GET /api/runs/{id}/stream endpoint can attach to a stored AsyncGenerator or replay from DB if the run is complete. This avoids refactoring the runner architecture while satisfying the requirement.

```python
# In-memory store for active run streams
_active_runs: dict[int, asyncio.Task] = {}

# GET /api/runs/{run_id}/stream
@router.get("/{run_id}/stream")
async def stream_run(run_id: int, request: Request) -> EventSourceResponse:
    run = get_run_from_db(run_id)
    if run.status == "completed":
        # Replay from DB as synthetic SSE events
        return EventSourceResponse(_replay_run_stream(run_id), ...)
    elif run_id in _active_runs:
        # Attach to live task — not simple with asyncio.Queue; see Pattern 3
        ...
    raise HTTPException(404)
```

### Pattern 3: Client Disconnect Cancels Task (API-10) — CRITICAL

**What:** When the browser tab closes or the network drops, the in-flight orchestrator `asyncio.Task` must be cancelled.

**How it works in sse-starlette:** `EventSourceResponse` from sse-starlette detects client disconnect via ASGI disconnect messages. When the client disconnects, sse-starlette stops consuming from the async generator. However, it does NOT cancel any background tasks that the generator may have spawned.

**The correct pattern** — wrap the generator with disconnect detection:

```python
# Source: FastAPI/Starlette disconnect pattern
async def run_with_disconnect_guard(
    request: Request,
    run_id: int,
    protocol_key: str,
    question: str,
    agent_keys: list[str],
) -> AsyncGenerator[str, None]:
    orch_task: asyncio.Task | None = None

    async def _inner():
        nonlocal orch_task
        async for event in run_protocol_stream(run_id, protocol_key, question, agent_keys):
            yield event

    gen = _inner()

    async def _watch_disconnect():
        await request.is_disconnected()  # blocks until disconnect
        if orch_task and not orch_task.done():
            orch_task.cancel()

    disconnect_task = asyncio.create_task(_watch_disconnect())
    try:
        async for event in gen:
            yield event
    finally:
        disconnect_task.cancel()
        if orch_task and not orch_task.done():
            orch_task.cancel()
```

**The harder piece:** `run_protocol_stream` creates `orch_task` internally as a local variable. For cancellation to work, the outer wrapper needs a reference to that task. Two approaches:

- **Shared dict approach:** `run_protocol_stream` registers `orch_task` in a module-level `_active_run_tasks: dict[int, asyncio.Task]` keyed by run_id. The disconnect guard looks it up and cancels it.
- **Refactor approach:** `run_protocol_stream` accepts an optional `task_registry` dict and inserts itself.

**Recommendation:** Use the shared `_active_run_tasks` dict in `api/runner.py`. Register on task creation, unregister in the finally block.

```python
# api/runner.py — add at module level
_active_run_tasks: dict[int, asyncio.Task] = {}

# In run_protocol_stream, after asyncio.create_task:
_active_run_tasks[run_id] = orch_task

# In the finally block:
_active_run_tasks.pop(run_id, None)
```

```python
# In the SSE endpoint handler:
async def _with_cancel(request: Request, gen) -> AsyncGenerator:
    async def _watch():
        while not await request.is_disconnected():
            await asyncio.sleep(0.5)
        task = _active_run_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            # Update run status to cancelled
            _mark_run_cancelled(run_id)

    watcher = asyncio.create_task(_watch())
    try:
        async for chunk in gen:
            yield chunk
    finally:
        watcher.cancel()
```

### Pattern 4: Context Var Isolation with copy_context (API-09)

**The bug:** In the current `run_protocol_stream`, context vars are set in the async generator body (which runs in the request context), then `asyncio.create_task()` is called. Python's `asyncio.create_task()` automatically copies the current `contextvars.Context` snapshot at task creation time. So the task DOES inherit the values — that part works.

**The actual problem:** `set_cost_tracker(None)` at the end of a run clears the ContextVar in the CURRENT context (the generator's context, which IS the task's copied context for the vars set before task creation). If two concurrent runs share the same event loop, and the ContextVar is a module-level global (not truly per-task), the clear from one run can affect another.

**The correct fix:** Set context vars INSIDE the task function, not before creating it:

```python
# api/runner.py — correct pattern for API-09
import contextvars

async def _run_protocol_task(run_id, protocol_key, question, agent_keys, ...):
    """Run inside asyncio.create_task — context vars set here are task-local."""
    cost_tracker = ProtocolCostTracker()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    # Set vars here — they are now isolated to this task's context copy
    set_cost_tracker(cost_tracker)
    set_event_queue(queue)
    try:
        result = await orchestrator.run(question)
        return result, cost_tracker, queue
    finally:
        set_cost_tracker(None)
        set_event_queue(None)
```

Since `run_protocol_stream` is itself an async generator (used as the SSE source), the orchestrator task needs to be structured so context vars are set within the spawned task, not in the generator. The cleanest approach is to pass the cost_tracker and queue as explicit parameters to a wrapper coroutine that sets the vars and runs the orchestrator, rather than relying on ContextVar propagation.

**Practical implementation:** Because ContextVars ARE propagated to tasks via copy at task creation (this is the Python spec), the real requirement for API-09 is: ensure the `asyncio.create_task()` call happens AFTER all context var assignments so the task captures the correct snapshot. This is already the case in the current code. The additional hardening needed is to NOT clear the vars at generator level (which is the currently-doing `set_cost_tracker(None)` after `yield run_complete`) and instead let the task's finally block handle cleanup.

**Confidence:** MEDIUM — the current code likely works for single concurrent runs; the fragility appears under parallel runs. The fix is low-risk: move set/clear to within the spawned coroutine.

### Pattern 5: Pipeline Presets (API-08)

**What:** GET /api/pipelines currently lists DB-stored pipeline records. The requirement adds "available pipeline presets (curated chains)." This means a hardcoded dict of 5-10 pre-defined multi-protocol chains that are always available (not requiring DB records).

**Implementation:** Add a `PIPELINE_PRESETS` constant dict in a new `api/pipeline_presets.py` module. The GET /api/pipelines endpoint returns the union of DB pipelines and presets.

```python
# api/pipeline_presets.py
PIPELINE_PRESETS = [
    {
        "id": "preset-strategy-deep-dive",
        "name": "Strategy Deep Dive",
        "description": "Cynefin domain mapping → TRIZ constraints → Red/Blue/White Team → Klein premortem",
        "is_preset": True,
        "steps": [
            {"protocol_key": "p23_cynefin_probe_sense_respond", "question_template": "{question}"},
            {"protocol_key": "p06_triz", "question_template": "Given domain analysis: {prev_output}\n\nQuestion: {question}"},
            {"protocol_key": "p17_red_blue_white_team", "question_template": "Stress-test: {prev_output}"},
            {"protocol_key": "p37_klein_premortem", "question_template": "Premortem for: {prev_output}"},
        ],
    },
    # ... additional presets
]
```

### Anti-Patterns to Avoid

- **Setting context vars after task creation:** If `set_cost_tracker()` is called after `asyncio.create_task()`, the task already has a snapshot of the old value. Set before creating the task, or set inside the task.
- **Not handling asyncio.CancelledError in the runner:** When `orch_task.cancel()` is called, the orchestrator raises `CancelledError`. The runner must catch it and mark the run as "cancelled" in the DB, not "failed."
- **Buffering proxy stripping SSE:** Nginx and Vercel's reverse proxy buffer responses by default. Without `X-Accel-Buffering: no`, events accumulate until the buffer fills. Always set this header on EventSourceResponse.
- **Calling `request.is_disconnected()` in a tight loop:** This is a polling call with real overhead. Poll every 0.5–1 second, not continuously.
- **Multi-worker deployment with in-process asyncio.Queue:** The STATE.md decision mandates single Uvicorn worker (INFR-07). The `_active_run_tasks` dict and asyncio.Queue are in-process. Never remove `--workers 1` from the uvicorn command.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE framing | Custom `text/event-stream` generator | `sse_starlette.EventSourceResponse` | Handles reconnect headers, keep-alives, proper framing |
| Client disconnect detection | Custom ASGI message polling | `request.is_disconnected()` (FastAPI/Starlette) | Starlette manages the ASGI scope disconnect signal |
| Async task lifecycle | Custom coroutine management | `asyncio.create_task()` + task.cancel() | Standard asyncio — handles CancelledError propagation |
| Context propagation | Thread locals or global mutable state | `contextvars.ContextVar` + copy_context | Python's built-in per-coroutine context isolation |

---

## Common Pitfalls

### Pitfall 1: sse-starlette does NOT cancel background tasks on disconnect
**What goes wrong:** The browser closes. sse-starlette stops iterating the generator. But `orch_task` keeps running in the event loop, burning API credits.
**Why it happens:** sse-starlette only controls generator iteration — it has no knowledge of tasks spawned inside the generator.
**How to avoid:** Maintain `_active_run_tasks: dict[int, asyncio.Task]` in runner.py. In the SSE endpoint, create a separate disconnect-watcher task that calls `task.cancel()` when `request.is_disconnected()` resolves.
**Warning signs:** Protocol runs with status "running" in the DB long after the client is gone.

### Pitfall 2: asyncio.CancelledError must update run status
**What goes wrong:** Task is cancelled, but the DB run record stays as "running" forever.
**Why it happens:** The `except Exception` block in runner.py doesn't catch `CancelledError` (it's a `BaseException`, not `Exception` in Python 3.8+).
**How to avoid:** Add explicit `except asyncio.CancelledError` handling in `run_protocol_stream` that marks the run as "cancelled" and re-raises.

```python
except asyncio.CancelledError:
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run:
            run.status = "cancelled"
            run.completed_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()
    raise  # Must re-raise CancelledError
```

### Pitfall 3: URL routing conflicts when adding /run sub-path to protocols router
**What goes wrong:** FastAPI route ordering matters. `GET /api/protocols/{key}/stages` and `POST /api/protocols/run` will conflict if "run" matches `{key}`.
**Why it happens:** FastAPI matches routes in order; `{key}` is a path parameter that matches any string including "run."
**How to avoid:** Define `POST /run` BEFORE `GET /{key}/stages` in the protocols router. FastAPI evaluates exact-match routes before parameterized routes when declared in that order.

### Pitfall 4: X-Accel-Buffering header missing from SSE responses
**What goes wrong:** Nginx/Vercel buffers SSE events; the client sees no events until the buffer fills or the stream ends.
**Why it happens:** The current `EventSourceResponse(...)` calls have no `headers=` argument.
**How to avoid:** Add `headers={"X-Accel-Buffering": "no"}` to every `EventSourceResponse(...)` call.

### Pitfall 5: Pipeline run URL conflict with runs router
**What goes wrong:** Both the runs router and the pipelines router want `/run` or `/pipeline` sub-paths; prefix collisions create 404s.
**Why it happens:** `pipelines` router is at `/api/pipelines`; adding `POST /run` is clean. But the current `POST /api/runs/pipeline` path will 404 clients expecting `/api/pipelines/run`.
**How to avoid:** Add `POST /run` to `api/routers/pipelines.py`. Remove or alias the old `POST /api/runs/pipeline`. The runs router becomes read-only (GET only).

---

## Code Examples

### Disconnect Watcher with Task Cancellation
```python
# Source: FastAPI docs on request disconnect + Python asyncio docs
# Pattern used in api/routers/protocols.py (to be created)

@router.post("/run")
async def start_protocol_run(
    payload: ProtocolRunRequest,
    request: Request,
) -> EventSourceResponse:
    with Session(engine) as session:
        run = Run(type="protocol", protocol_key=payload.protocol_key,
                  question=payload.question, status="pending")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    async def _guarded_stream():
        disconnect_watcher = asyncio.create_task(_watch_disconnect(request, run_id))
        try:
            async for chunk in run_protocol_stream(
                run_id=run_id,
                protocol_key=payload.protocol_key,
                question=payload.question,
                agent_keys=payload.agent_keys,
                thinking_model=payload.thinking_model,
                orchestration_model=payload.orchestration_model,
                rounds=payload.rounds,
                no_tools=payload.no_tools,
            ):
                yield chunk
        finally:
            disconnect_watcher.cancel()

    return EventSourceResponse(
        _guarded_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


async def _watch_disconnect(request: Request, run_id: int) -> None:
    while not await request.is_disconnected():
        await asyncio.sleep(0.5)
    task = _active_run_tasks.get(run_id)
    if task and not task.done():
        task.cancel()
```

### Registering Active Tasks in runner.py
```python
# Source: Python asyncio docs — task lifecycle management
# api/runner.py additions

_active_run_tasks: dict[int, asyncio.Task] = {}

async def run_protocol_stream(run_id, protocol_key, ...):
    ...
    orch_task = asyncio.create_task(orchestrator.run(question))
    _active_run_tasks[run_id] = orch_task          # Register for cancellation
    orch_task.add_done_callback(lambda t: _active_run_tasks.pop(run_id, None))
    ...
    except asyncio.CancelledError:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "cancelled"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()
        yield _sse_event("run_complete", {"run_id": run_id, "status": "cancelled"})
        raise
```

### GET /api/runs/{id}/stream (Replay or Live)
```python
# api/routers/runs.py — new GET endpoint
@router.get("/{run_id}/stream")
async def stream_run(
    run_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> EventSourceResponse:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in ("completed", "failed", "cancelled"):
        return EventSourceResponse(
            _replay_completed_run(run_id, session),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    # Live run — attach disconnect watcher and stream
    # The run is still being produced by the POST endpoint's generator
    # For Phase 5, return 202 with a polling hint if no live attachment
    raise HTTPException(status_code=202, detail="Run in progress; poll GET /api/runs/{id}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global mutable state for request context | `contextvars.ContextVar` | Python 3.7+ | Per-coroutine isolation without thread locals |
| Manual SSE framing | `sse-starlette EventSourceResponse` | 2021+ | Proper keep-alive, reconnect ID handling |
| Polling for completion | SSE push events | Phase 5 | Real-time progress without client polling |
| `asyncio.CancelledError` is `Exception` | `CancelledError` is `BaseException` (Python 3.8+) | Python 3.8 | Must use `except asyncio.CancelledError`, NOT `except Exception` |

---

## What's Already Implemented (Do NOT Rebuild)

This is critical context for the planner. Large portions of the phase requirements are already done:

| Requirement | Status | Location |
|-------------|--------|----------|
| API-03: GET /api/protocols | DONE | api/routers/protocols.py |
| API-04: GET /api/agents with @group expansion | DONE | api/routers/agents.py |
| API-05: GET /api/runs with pagination | DONE | api/routers/runs.py |
| API-06: GET /api/runs/{id} with outputs | MOSTLY DONE (missing trace link) | api/routers/runs.py |
| SSE streaming infrastructure | DONE | api/runner.py + sse-starlette |
| Run persistence (SQLite + Postgres) | DONE | api/runner.py + protocols/persistence.py |
| Cost tracking integration | DONE | api/runner.py |
| Pipeline chaining with prev_output | DONE | api/runner.py run_pipeline_stream |

The planner should structure tasks around the GAPS, not rebuild what's working.

---

## Open Questions

1. **GET /api/runs/{id}/stream for live runs**
   - What we know: The current POST /api/protocols/run returns SSE inline. The run_id is only known after the stream starts (via the run_start event).
   - What's unclear: Does the UI need to connect to a separate GET endpoint, or can it consume the POST SSE directly?
   - Recommendation: For Phase 5, implement the GET /stream endpoint that replays completed runs and returns 202 for in-progress. The UI can connect to POST directly for live progress. A full "reconnectable SSE" pattern (storing a queue per run_id and allowing multiple consumers) is SCAL-01 scope (v2).

2. **Pipeline preset content**
   - What we know: API-08 requires curated chains to be returned by GET /api/pipelines.
   - What's unclear: Which specific protocol combinations to include. The ROADMAP references UI-08/UI-09 for a curated "greatest hits" collection.
   - Recommendation: Define 5-6 named presets in a hardcoded module. Specific protocols: Strategy Deep Dive (Cynefin → TRIZ → Red/Blue Team), Risk Analysis (Klein Premortem → Tetlock Forecast), Innovation Sprint (Crazy Eights → Affinity Mapping → Constraint Negotiation). Exact selection can be refined at implementation time.

3. **Langfuse trace link in GET /api/runs/{id}**
   - What we know: The `trace_id` is stored in the `run_complete` SSE event and passed to `persist_run`. It is NOT stored in the SQLite `Run` model.
   - What's unclear: Whether trace_id is being saved to SQLite or only to Postgres.
   - Recommendation: Add `trace_id` column to the SQLite `Run` model and populate it from the `run_complete` event payload. This is a minor schema migration (SQLModel auto-creates on startup if missing).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (inferred from existing tests) |
| Config file | none — no pytest.ini or pyproject.toml found; pytest discovers tests/ directory |
| Quick run command | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && pytest tests/test_runs_api.py tests/test_protocols_api.py -x -q` |
| Full suite command | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && pytest tests/ -m "not integration" -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | POST /api/protocols/run creates run record | unit | `pytest tests/test_runs_api.py -k "test_protocol_run" -x` | ❌ Wave 0 |
| API-02 | SSE response has X-Accel-Buffering: no header | unit | `pytest tests/test_runs_api.py -k "test_sse_headers" -x` | ❌ Wave 0 |
| API-03 | GET /api/protocols returns list >= 48 | unit | `pytest tests/test_protocols_api.py::test_protocols_endpoint_returns_list -x` | ✅ |
| API-04 | GET /api/agents returns agent list | unit | `pytest tests/test_runs_api.py -k "test_agents" -x` | ❌ Wave 0 |
| API-05 | GET /api/runs returns paginated list | unit | `pytest tests/test_runs_api.py -k "test_list_runs" -x` | ❌ Wave 0 |
| API-06 | GET /api/runs/{id} returns full detail | unit | `pytest tests/test_runs_api.py -k "test_get_run" -x` | ❌ Wave 0 |
| API-07 | POST /api/pipelines/run creates run | unit | `pytest tests/test_runs_api.py -k "test_pipeline_run" -x` | ❌ Wave 0 |
| API-08 | GET /api/pipelines returns presets | unit | `pytest tests/test_runs_api.py -k "test_pipeline_presets" -x` | ❌ Wave 0 |
| API-09 | Context vars isolated per task | unit | `pytest tests/test_runs_api.py -k "test_context_var" -x` | ❌ Wave 0 |
| API-10 | Client disconnect cancels orchestrator task | unit | `pytest tests/test_runs_api.py -k "test_disconnect_cancels" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_runs_api.py tests/test_protocols_api.py -x -q`
- **Per wave merge:** `pytest tests/ -m "not integration" -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_runs_api.py` — needs significant expansion (currently only has 5 schema validation tests; needs endpoint tests via TestClient)
- [ ] `tests/conftest.py` — shared TestClient fixture with in-memory SQLite DB override
- [ ] Add `conftest.py` with `@pytest.fixture def client()` using `TestClient(app)` and engine override
- [ ] Ensure `httpx` is installed (FastAPI TestClient dependency): `pip install httpx`

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `api/runner.py`, `api/routers/runs.py`, `api/routers/protocols.py`, `api/routers/agents.py`, `api/routers/pipelines.py`, `api/models.py`, `api/server.py`, `api/database.py`, `api/manifest.py`
- Direct inspection of existing tests in `tests/test_runs_api.py`, `tests/test_protocols_api.py`
- Python stdlib docs — `asyncio.create_task()` copies current Context snapshot (Python 3.7+ behavior)
- Python stdlib docs — `asyncio.CancelledError` is `BaseException` not `Exception` (Python 3.8+)

### Secondary (MEDIUM confidence)
- sse-starlette v3.2.0 installed in project venv — `EventSourceResponse` accepts `headers=` parameter
- Starlette `request.is_disconnected()` pattern — standard approach documented in Starlette source

### Tertiary (LOW confidence)
- Vercel SSE buffering behavior — not directly tested; X-Accel-Buffering header is the standard Nginx/reverse-proxy directive and is used by Vercel's proxy layer based on community reports

---

## Metadata

**Confidence breakdown:**
- What's already implemented: HIGH — direct code inspection
- Gap analysis (API-01, API-07 URL mismatch): HIGH — confirmed by router inspection
- API-09 (context var bug): MEDIUM — logic analysis; the bug is subtle and may not manifest in single-concurrent-run scenarios
- API-10 (disconnect cancel): HIGH — confirmed absent from router and runner
- API-02 (X-Accel-Buffering): HIGH — confirmed absent from EventSourceResponse calls
- Pipeline presets content: LOW — specific protocol selections are a product decision, not a technical one

**Research date:** 2026-03-10
**Valid until:** 2026-06-10 (FastAPI and sse-starlette are stable; asyncio behavior is stable)
