# Project Research Summary

**Project:** CE-AGENTS Full-Stack Integration
**Domain:** Multi-agent AI orchestration platform — consulting delivery product
**Researched:** 2026-03-10
**Confidence:** HIGH

## Executive Summary

CE-AGENTS is a multi-agent AI orchestration platform that already has most of its machinery built: 52 protocols, a FastAPI backend with SSE infrastructure, a React frontend with Zustand stores, PostgreSQL persistence, Langfuse tracing, and a quality scoring system. The integration work is a wiring problem, not a greenfield build. The core gap is that routers are stubs, the frontend and backend are not connected, auth does not exist, CORS is hardcoded to localhost, agent imports break in Docker, and there is no structured output format for presenting results to clients. Close these gaps in dependency order and the product is deployable within the current sprint.

The recommended approach is a six-layer build sequence driven by the dependency graph in the feature research: fix the agent path first (everything else depends on production-mode agents running), then wire the API endpoints, then define the ProtocolReport output format, then add auth, then add PDF export, and finally containerize and deploy. Each layer is independently testable. Serving the React SPA from FastAPI StaticFiles eliminates the CORS problem entirely and simplifies auth for SSE. Railway Hobby ($5/mo) is the deployment target — it handles Postgres, avoids free-tier sleep kills, and supports long-running protocol executions up to 120 seconds.

The top risks are not architectural — the architecture is sound. They are operational: SSE proxy buffering will silently destroy the streaming experience unless headers are set at first implementation; Docker COPY with spaces in directory names will silently fail to copy the Agent Builder source; and silent fallback from production to research agent mode will cause Scott to deliver inferior output to clients with no warning. All three are prevention problems, not recovery problems — they must be addressed in the phases where they are introduced, not discovered afterward.

---

## Key Findings

### Recommended Stack

The existing stack (FastAPI, React 19, PostgreSQL 16, Vite 7, Tailwind 4, Zustand) is correct and requires no changes. Six additions are needed: `PyJWT>=2.11.0` and `pwdlib[argon2]>=0.3.0` for auth (replacing the abandoned `python-jose` and deprecated `passlib`); `WeasyPrint>=68.1` and `Jinja2>=3.1.0` for PDF report generation; `@microsoft/fetch-event-source@2.0.1` for SSE from React (native `EventSource` cannot send POST bodies or auth headers); and `sse-starlette>=2.0.0` (bump from current `>=1.8.0` for rewritten async core).

**Core technologies:**
- FastAPI + sse-starlette: REST API and SSE streaming — existing infrastructure, needs stub routers filled
- React 19 + Zustand: Frontend with stores already defined — needs API connection to replace mock data
- PostgreSQL 16 + SQLAlchemy async: Primary data store — must consolidate SQLite-backed agent/team/pipeline records
- PyJWT + pwdlib[argon2]: Auth — modern replacements for abandoned python-jose and deprecated passlib
- WeasyPrint + Jinja2: PDF export — HTML templates serve dual use for browser view and PDF generation
- @microsoft/fetch-event-source: SSE client — only option supporting POST + custom auth headers
- Railway Hobby: Deployment — $5/mo, native FastAPI + Postgres, no free-tier sleep kills

### Expected Features

**Must have (table stakes — blocks client use):**
- Protocol execution from browser with live SSE progress — core value; 30-120 second runs require live feedback
- ProtocolReport structured output format — raw JSON is not a consulting deliverable
- Run history list and re-open — "show me last week's runs before the Acme meeting" is a real workflow
- Simple JWT auth login gate — client URLs cannot be publicly accessible
- Cloud deployment with accessible URL — clients need a URL, not a screenshare of localhost

**Should have (differentiators — first sprint after MVP):**
- PDF/doc export — consulting deliverable is a report, not a browser session
- Protocol chains as packaged workflows — "Run Cynefin → TRIZ → Popper" as a named engagement
- Curated "greatest hits" collection — 52 protocols is overwhelming; surface 8-10 best
- Agent disagreement highlighting — clients pay for where agents diverge
- Confidence level display — signal consensus vs. speculation

**Defer with confidence (v2+):**
- Custom protocol builder UI — protocols are complex Python; drag-and-drop produces inferior output
- Multi-user RBAC — Scott is sole operator; read-only URL sharing is sufficient
- Real-time token streaming — protocols are multi-stage batch operations, not chat
- CE-Evals UI integration — evaluation is a separate CLI research workflow
- Cost estimate pre-run — a few hours of work once token estimation (Phase 3) is wired; not blocking

### Architecture Approach

The target architecture is a single-origin deployment: React SPA served as static files from FastAPI StaticFiles, eliminating CORS entirely. A single Uvicorn worker is required because SSE event queues are in-process `asyncio.Queue` objects — multi-worker deployments silently drop events. All data moves to PostgreSQL (SQLite-backed agent/team/pipeline records are lost on container restart). Auth uses JWT access tokens with session cookies for SSE endpoints (native EventSource cannot send Authorization headers).

**Major components:**
1. API layer (`api/`) — 7 routers (protocols, runs, agents, pipelines, teams, auth, reports); currently stubs; implementing these is the primary work
2. Protocol execution engine (`api/runner.py`) — already complete; SSE event queue, async generator, quality scoring all working
3. Agent layer (`agent_provider.py`) — needs absolute path fix for Docker; must assert production mode on startup before accepting requests
4. ProtocolReport format — new shared dataclass transforming per-protocol result types into unified presentation layer for UI and PDF
5. Report export (`api/routers/reports.py`) — new router; Jinja2 template → WeasyPrint → PDF streaming response
6. PostgreSQL (ce-db) — consolidate all data here; seed agents from protocols/agents.py registry on first startup

### Critical Pitfalls

1. **SSE proxy buffering kills streaming in production** — Add `X-Accel-Buffering: no` to every SSE response at the time the endpoint is wired, not after deployment. Works on localhost, silently broken behind any reverse proxy.

2. **Silent production agent mode fallback** — Add startup assertion verifying SdkAgent import succeeds before accepting any API requests. Log agent mode at run start. Never silently fall back to research mode — fail loudly. Silent fallback means Scott delivers inferior client output with no indication anything is wrong.

3. **Docker COPY with spaces in directory names** — Always use JSON array form: `COPY ["CE - Agent Builder/", "/app/agent-builder/"]`. Standard shell form treats spaces as argument separators and silently copies nothing. Docker build succeeds; runtime fails with ModuleNotFoundError.

4. **CORS whitelist hardcoded to localhost** — Load allowed origins from env var. Serving React from FastAPI StaticFiles eliminates this entirely; if serving separately, `allow_origins=["*"]` with `allow_credentials=True` is mutually exclusive per CORS spec.

5. **Context vars set in wrong async context** — Set `_cost_tracker` and `_event_queue` context vars inside the `asyncio.create_task()` coroutine, not in the request handler. Concurrent runs share or corrupt cost data and event routing if set in the handler context.

---

## Implications for Roadmap

The dependency graph from FEATURES.md dictates phase order. Each layer unblocks the next; no phase can be usefully tested until its dependencies are complete.

### Phase 1: Fix Agent Provider and Production Mode Assertion

**Rationale:** Everything downstream depends on production-mode SdkAgents running correctly in whatever environment the API starts in. This is a precondition, not a feature — but it silently breaks client output quality if skipped.
**Delivers:** Guaranteed production agent mode at API startup; explicit startup failure if SdkAgent cannot be imported
**Addresses:** Table stakes — protocol execution requires real agents with tools, MCP servers, and memory
**Avoids:** C-2 (silent production fallback), Docker runtime ModuleNotFoundError

### Phase 2: Wire API Endpoints

**Rationale:** The runner, SSE infrastructure, and Zustand stores are already built. The missing layer is the router implementations connecting them. This is the highest-leverage work in the project — filling 7 stub routers unlocks protocol execution, run history, and cost tracking in one phase.
**Delivers:** Working protocol execution from browser with live streaming; run history; agent list; cost display per run
**Addresses:** Protocol execution, live streaming progress, run history, re-open past run, cost display
**Avoids:** C-1 (SSE buffering headers baked in from the start), C-4 (async DB sessions), M-1 (task cancellation on client disconnect), M-2 (context vars inside task)
**Uses:** sse-starlette async generator pattern, asyncio.Queue event drain, X-Accel-Buffering header

### Phase 3: ProtocolReport Structured Output Format

**Rationale:** Protocol runs complete end-to-end in Phase 2 but output raw JSON. This phase makes results usable for consulting delivery. It is also the foundation for PDF export, disagreement highlighting, confidence display, and shareable URLs — all downstream features depend on this format being defined first.
**Delivers:** Executive-readable structured output with participants, findings, disagreements, confidence, synthesis, per-agent contributions; UI components rendering each section
**Addresses:** Structured result display, agent disagreement highlighting, confidence display, per-agent contribution view
**Uses:** Shared `ProtocolReport` dataclass transforming per-protocol result types into unified presentation layer

### Phase 4: Auth + Frontend Wiring

**Rationale:** Auth is required before deployment. SSE auth is non-trivial (native EventSource cannot send headers) and must be solved with `@microsoft/fetch-event-source` or session cookies — not query-param tokens (which appear in logs and browser history). CORS must move to env var in this phase.
**Delivers:** JWT login gate, protected routes, SSE auth, CORS from env var, React auth context, cookie-based session for SSE
**Addresses:** Login gate, client URL access (auth must work at cloud domain)
**Avoids:** M-3 (EventSource auth), C-3 (CORS hardcoded to localhost)
**Uses:** PyJWT, pwdlib[argon2], @microsoft/fetch-event-source

### Phase 5: PDF Report Export

**Rationale:** Consulting deliverable is a report, not a browser session. Isolating WeasyPrint in its own phase means Docker system package issues don't block the deployment phase — validate WeasyPrint in container before building the full production image.
**Delivers:** PDF download button on run view; polished client-deliverable reports using Jinja2 HTML templates
**Addresses:** Export to polished PDF/doc (differentiator)
**Avoids:** M-4 (WeasyPrint system deps in Docker — verified in this phase, not discovered in Phase 6)
**Uses:** WeasyPrint, Jinja2; same HTML templates serve browser view and PDF generation

### Phase 6: Docker + Cloud Deployment

**Rationale:** All features are wired and tested locally. This phase packages for production and validates every integration at the real deployment URL. All pitfalls identified in deployment research are resolved here.
**Delivers:** Working cloud URL (Railway), one-command local startup (Makefile), end-to-end smoke test through production proxy
**Addresses:** Cloud URL access, one-command local startup
**Avoids:** C-5 (Docker COPY with spaces), C-3 (CORS at cloud domain), M-5 (free-tier sleep — use Railway paid tier), M-6 (Alembic migration state drift before promote)
**Uses:** Railway, multi-stage Dockerfile, docker-compose extending existing Postgres config, Makefile

### Phase Ordering Rationale

- Phase 1 before everything: production agent mode is a precondition; all output quality depends on it; silent failure here poisons every downstream phase
- Phase 2 before auth: endpoint stubs must exist before auth middleware wraps them; also faster iteration without auth in the way during development
- Phase 3 before auth: ProtocolReport format must be defined before shareable URLs (Phase 4) have anything structured to display
- Phase 4 before deployment: cannot deploy a system with no auth and localhost-only CORS
- Phase 5 before deployment: WeasyPrint Docker system dependencies must be in the Dockerfile and verified in-container before the production image is built
- Phase 6 last: validates the complete stack end-to-end in the real environment after all pieces are assembled

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Auth):** SSE auth pattern has non-obvious tradeoffs between `@microsoft/fetch-event-source` (adds npm dependency, minimally maintained) vs. session cookies after JWT verify (simpler but requires cookie path configuration); confirm approach before implementing
- **Phase 6 (Deployment):** Railway-specific request timeout configuration for 120s+ protocol runs needs verification against actual Railway Hobby plan behavior

Phases with standard patterns (skip research-phase):
- **Phase 1 (Agent Provider Fix):** One targeted change — env var path, startup assertion; well-understood, no unknowns
- **Phase 2 (API Endpoints):** Standard FastAPI CRUD + SSE patterns; architecture is fully designed in ARCHITECTURE.md with data flow diagrams
- **Phase 3 (ProtocolReport):** Dataclass design + UI components; no novel integration; shape is clear from existing per-protocol result dataclasses
- **Phase 5 (PDF Export):** WeasyPrint + Jinja2 pattern is well-documented; main risk (Docker deps) already identified and mitigated

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommendations based on official docs and direct PyPI/npm inspection; version compatibility verified; deprecated library replacements confirmed |
| Features | HIGH | Based on direct codebase inspection — what exists vs. what is a stub; dependency graph derived from actual code, not inference |
| Architecture | HIGH | Based on reading actual source files: runner.py, server.py, agent_provider.py, all router stubs; no speculation required |
| Pitfalls | HIGH | All pitfalls derived from actual code patterns observed in the codebase; not generic web advice; specific line-level issues identified |

**Overall confidence:** HIGH

### Gaps to Address

- **WeasyPrint on Railway:** System package availability (`libpango-1.0-0`, `libharfbuzz0b`, `libffi-dev`, `libgdk-pixbuf-2.0-0`) in Railway's Docker build environment is unverified. Mitigate: add a smoke test that builds the Docker image and generates a PDF before Phase 6 declares done.
- **@microsoft/fetch-event-source maintenance status:** Last commit approximately 2 years ago. If issues arise, fallback is GET-based SSE with run config persisted first via POST. Flag in Phase 4 planning to confirm the approach before implementation begins.
- **SQLite-to-PostgreSQL migration scope:** Agent, team, and pipeline records currently in SQLite need a migration plan. Likely a seed script from `protocols/agents.py` registry rather than a data migration. Confirm scope and approach at start of Phase 2.
- **Railway request timeout limits:** Long protocol runs (up to 120s) require confirming Railway Hobby plan supports request timeouts at that duration. Check before starting Phase 6.

---

## Sources

### Primary (HIGH confidence — direct source inspection)
- `api/runner.py` — SSE infrastructure, event queue, production/research mode, context vars pattern
- `api/server.py` — CORS config, existing middleware, static file patterns
- `api/agent_provider.py` — sys.path fragility, Docker space issue
- `protocols/agents.py` — 56-agent registry, group syntax
- FastAPI security docs (2025) — PyJWT + pwdlib[argon2] recommendation
- sse-starlette PyPI (v3.3.2 current) — async core rewrite in v2.0+
- WeasyPrint v68.1 PyPI — system dependency requirements

### Secondary (MEDIUM confidence)
- Railway docs — pricing, Postgres 16 managed, deployment capabilities
- @microsoft/fetch-event-source npm — POST + auth header support for SSE

### Tertiary (LOW confidence — needs validation)
- Railway request timeout limits for long-running HTTP connections — verify before Phase 6

---
*Research completed: 2026-03-10*
*Ready for roadmap: yes*
