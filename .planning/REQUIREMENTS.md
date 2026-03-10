# Requirements: CE-AGENTS Full-Stack Integration

**Defined:** 2026-03-10
**Core Value:** A client question goes in, a structured multi-agent analysis comes out — viewable in a browser, exportable as a polished report, powered by production agents with tools and memory.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Agent Provider

- [x] **AGNT-01**: Agent provider uses absolute path (env var) instead of fragile sys.path.insert for SdkAgent imports
- [x] **AGNT-02**: API startup asserts SdkAgent import succeeds before accepting requests — fails loudly if production mode unavailable
- [x] **AGNT-03**: Production mode is the default agent mode; research mode requires explicit opt-in

### API Endpoints

- [x] **API-01**: POST /api/protocols/run accepts protocol name, question, and agent list, executes orchestrator, returns run ID
- [x] **API-02**: GET /api/runs/{id}/stream delivers SSE events (stage_start, stage_complete, tool_call, run_complete) with X-Accel-Buffering: no header
- [x] **API-03**: GET /api/protocols returns list of all available protocols with name, description, category, and stage metadata
- [x] **API-04**: GET /api/agents returns agent registry with name, role, category, and @group expansion
- [x] **API-05**: GET /api/runs returns paginated run history with protocol, question, cost, status, timestamp
- [x] **API-06**: GET /api/runs/{id} returns full run detail including result, agent outputs, cost breakdown, Langfuse trace link
- [x] **API-07**: POST /api/pipelines/run executes a protocol chain, passing each protocol's output as context to the next
- [x] **API-08**: GET /api/pipelines returns available pipeline presets (curated chains)
- [x] **API-09**: Context vars (cost_tracker, event_queue) are set inside asyncio task, not in request handler
- [x] **API-10**: Client disconnect cancels the orchestrator asyncio task to stop burning API credits

### Structured Output

- [ ] **OUT-01**: ProtocolReport shared dataclass with fields: participants, key_findings, disagreements, confidence_score, synthesis, agent_contributions, cost_summary, metadata
- [ ] **OUT-02**: All protocol result dataclasses transform into ProtocolReport for consistent presentation
- [ ] **OUT-03**: Browser view renders ProtocolReport with scannable sections — executive summary at top, agent detail on expand
- [ ] **OUT-04**: Agent disagreement sections are visually highlighted in the browser view
- [ ] **OUT-05**: Confidence/quality score displays as a visual indicator (not raw number)
- [ ] **OUT-06**: Per-agent contribution cards show what each agent contributed to the analysis

### Report Export

- [ ] **REPT-01**: GET /api/reports/{run_id}/pdf generates a polished PDF from ProtocolReport via WeasyPrint + Jinja2 template
- [ ] **REPT-02**: PDF report includes executive summary, key findings, disagreements, agent contributions, and cost metadata
- [ ] **REPT-03**: Browser-viewable HTML report at a shareable URL (GET /runs/{id}) with read-only access for clients

### Frontend Integration

- [ ] **UI-01**: Protocol library page loads real protocol data from API with search/filter by category
- [ ] **UI-02**: Protocol execution form: select protocol, enter question, pick agents (with @category shortcuts), submit
- [ ] **UI-03**: Live execution view shows streaming SSE events (stages progressing, tools being called)
- [ ] **UI-04**: Run result view renders ProtocolReport structured output with all sections
- [ ] **UI-05**: Run history page loads real data from API with search/filter
- [ ] **UI-06**: Re-open past run shows full ProtocolReport without re-executing
- [ ] **UI-07**: Cost displayed per run in history and detail views
- [ ] **UI-08**: Curated "greatest hits" protocol collection surfaced prominently (8-10 best protocols for common consulting questions)
- [ ] **UI-09**: Protocol chain builder or preset selector for packaged workflows
- [ ] **UI-10**: Download PDF button on run detail page

### Authentication

- [ ] **AUTH-01**: Users table with email + argon2 password hash (Alembic migration)
- [ ] **AUTH-02**: POST /api/auth/login returns JWT access token + sets session cookie for SSE
- [ ] **AUTH-03**: All API endpoints require valid JWT (except /api/auth/login and /api/health)
- [ ] **AUTH-04**: SSE endpoints accept session cookie for auth (EventSource cannot send custom headers)
- [ ] **AUTH-05**: CORS allowed origins loaded from environment variable, not hardcoded to localhost
- [ ] **AUTH-06**: React auth context with login page, protected routes, and token refresh

### Infrastructure

- [ ] **INFR-01**: Dockerfile with multi-stage build — Python backend + React static build served by FastAPI StaticFiles
- [ ] **INFR-02**: docker-compose.yml extended with API server + UI build for one-command local startup
- [ ] **INFR-03**: Makefile with `make dev` (local full stack), `make build` (Docker), `make deploy` (Vercel)
- [ ] **INFR-04**: Cloud deployment to Vercel with FastAPI backend + static frontend accessible via URL
- [ ] **INFR-05**: Managed PostgreSQL accessible from Vercel deployment (Vercel Postgres or external)
- [ ] **INFR-06**: Getting-started documentation: setup script or step-by-step for first-time environment config
- [ ] **INFR-07**: Single Uvicorn worker enforced (asyncio.Queue SSE is in-process; multi-worker silently drops events)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Output

- **ADV-01**: Cost estimate before run (/api/protocols/estimate endpoint)
- **ADV-02**: Protocol diagram view showing multi-stage flow before execution
- **ADV-03**: Word/DOCX export option alongside PDF
- **ADV-04**: Langfuse trace deep-link from run detail view

### Multi-User

- **MUSR-01**: Role-based access control (admin, analyst, client-viewer)
- **MUSR-02**: Team workspaces with shared run history
- **MUSR-03**: Client portal with read-only access to selected runs

### Scale

- **SCAL-01**: Redis pub/sub for cross-worker SSE (enables multi-worker deployment)
- **SCAL-02**: Background job queue for protocol runs (not tied to request lifecycle)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom protocol builder UI | Protocols are complex multi-stage Python; a UI builder produces inferior output |
| Real-time collaborative runs | SSE is single-subscriber; multi-user presence is a separate product |
| Mobile / responsive UI | Client meetings use laptop browser; desktop-first is sufficient |
| CE-Evals integration into UI | Evaluation is a separate research workflow |
| Self-hosted Langfuse | Cloud Langfuse already working |
| QuickBooks / billing integration | Billing handled outside platform |
| Agent builder UI | Agent config is complex Python with MCP server wiring |
| Real-time token streaming | Protocols are multi-stage batch operations, not chat |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGNT-01 | Phase 4 | Complete |
| AGNT-02 | Phase 4 | Complete |
| AGNT-03 | Phase 4 | Complete |
| API-01 | Phase 5 | Complete |
| API-02 | Phase 5 | Complete |
| API-03 | Phase 5 | Complete |
| API-04 | Phase 5 | Complete |
| API-05 | Phase 5 | Complete |
| API-06 | Phase 5 | Complete |
| API-07 | Phase 5 | Complete |
| API-08 | Phase 5 | Complete |
| API-09 | Phase 5 | Complete |
| API-10 | Phase 5 | Complete |
| OUT-01 | Phase 6 | Pending |
| OUT-02 | Phase 6 | Pending |
| OUT-03 | Phase 6 | Pending |
| OUT-04 | Phase 6 | Pending |
| OUT-05 | Phase 6 | Pending |
| OUT-06 | Phase 6 | Pending |
| REPT-01 | Phase 6 | Pending |
| REPT-02 | Phase 6 | Pending |
| REPT-03 | Phase 6 | Pending |
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |
| UI-06 | Phase 7 | Pending |
| UI-07 | Phase 7 | Pending |
| UI-08 | Phase 7 | Pending |
| UI-09 | Phase 7 | Pending |
| UI-10 | Phase 7 | Pending |
| AUTH-01 | Phase 7 | Pending |
| AUTH-02 | Phase 7 | Pending |
| AUTH-03 | Phase 7 | Pending |
| AUTH-04 | Phase 7 | Pending |
| AUTH-05 | Phase 7 | Pending |
| AUTH-06 | Phase 7 | Pending |
| INFR-01 | Phase 8 | Pending |
| INFR-02 | Phase 8 | Pending |
| INFR-03 | Phase 8 | Pending |
| INFR-04 | Phase 8 | Pending |
| INFR-05 | Phase 8 | Pending |
| INFR-06 | Phase 8 | Pending |
| INFR-07 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 — traceability updated to v1.1 phase numbering (4-8)*
