---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Full-Stack Integration
status: planning
stopped_at: Phases 4-6 complete; Phases 7-8 superseded by the Clerk + cardinal-portal + Railway productization track — v1.2 (Phases 9-12) next
last_updated: "2026-07-01"
last_activity: 2026-07-01 — State refreshed during repo audit; roadmap v1.2 recorded
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 17
  completed_plans: 17
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A client question goes in, a structured multi-agent analysis comes out — viewable in a browser, exportable as a polished report, powered by production agents with tools and memory.
**Current focus:** Phase 7 — Frontend and Auth (next up)

## Current Position

Phase: 7 of 8 (Frontend and Auth)
Plan: 0 of 3 in current phase
Status: Ready to plan
Last activity: 2026-07-01 — State refreshed during repo audit

Progress: [██████░░░░] 60% (v1.1 milestone — phases 4-6 complete; 7-8 outcomes shipped via the Clerk/cardinal-portal/Railway track outside this roadmap; v1.2 phases 9-12 pending)

> **2026-07-01 note:** frontend auth and deployment (Phases 7-8) were ultimately delivered as `cardinal-portal` (Next.js + Clerk on Vercel) + the Railway FastAPI deployment rather than the plans written here — see root `CLAUDE.md` "Productization stack". Deployment decision below ("Vercel not Railway") is superseded: the API engine runs on Railway, the portal on Vercel.

## Performance Metrics

**Velocity (from v1.0):**
- Total plans completed: 12
- Average duration: 2.1 min
- Total execution time: ~0.4 hours

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Shared Package | 3 | ~7 min | 2.3 min |
| 2. Env Consolidation | 5 | ~11 min | 2.2 min |
| 3. Token Estimation | 4 | ~7 min | 1.75 min |

**Recent Trend:**
- Last 5 plans: 2, 2, 3, 2, 2 min
- Trend: Stable
| Phase 04-agent-provider P01 | 6 | 2 tasks | 5 files |
| Phase 05-api-wiring P01 | 8 | 2 tasks | 7 files |
| Phase 05-api-wiring P02 | 8 | 2 tasks | 5 files |
| Phase 06-structured-output-and-reports P01 | 6 | 2 tasks | 6 files |

## Accumulated Context

### Decisions

- **Phase 1-1:** Opus 4.6 = $5/$25 pricing confirmed; unknown models default to Opus-tier as conservative fallback
- **Phase 3-2:** Cost ceiling is warn-only, never halts execution
- **2026-03-10:** Deployment target is Vercel (not Railway — user corrected during project init)
- **2026-03-10:** Single Uvicorn worker required — SSE event queues are in-process asyncio.Queue, multi-worker silently drops events (INFR-07)
- **2026-03-10:** Serve React SPA from FastAPI StaticFiles — eliminates CORS problem entirely for same-origin deployment
- [Phase 04-agent-provider]: Production is the default agent mode — research mode requires explicit opt-in via set_agent_mode() or AGENT_MODE env var
- [Phase 04-agent-provider]: Hard failure on ANY agent instantiation error: all agents must load as SdkAgent, no partial results
- [Phase 04-agent-provider]: CE_AGENT_BUILDER_PATH env var overrides computed sibling-directory path — enables Docker and non-standard layouts
- [Phase 05-api-wiring]: POST /api/protocols/run and POST /api/pipelines/run are the canonical run URLs; old POST /api/runs/protocol and /pipeline removed
- [Phase 05-api-wiring]: All SSE EventSourceResponse always include X-Accel-Buffering: no header to prevent proxy buffering
- [Phase 05-api-wiring]: Re-raise asyncio.CancelledError after handling: required so asyncio task machinery marks the task as cancelled and propagates through awaiter chains
- [Phase 05-api-wiring]: Disconnect watcher polls request.is_disconnected() every 0.5s: balances responsiveness with polling overhead for long-running protocol runs
- [Phase 05-api-wiring]: Pipeline presets use verified protocol key names from actual protocols/ directory (p38_klein_premortem, p17_red_blue_white, p23_cynefin_probe)
- [Phase Phase 06-01]: ProtocolReport lives in protocols/ not api/ — avoids circular dependency, UI layer is in api/
- [Phase Phase 06-01]: protocol_report only populated for completed runs — pending/failed runs return null to avoid incomplete data
- [Phase Phase 06-02]: asyncio.to_thread() for WeasyPrint write_pdf() — avoids blocking FastAPI event loop during PDF generation
- [Phase Phase 06-02]: protocolReport fetched separately after SSE run_complete event — keeps SSE stream format clean, avoids protocol_report in stream payload

### Pending Todos

- Review ACI collective intelligence layer recommendation (from v1.0 session)
- See .planning/todos/pending/

### Blockers/Concerns

- WeasyPrint Docker system package availability on Vercel unverified — smoke test required before Phase 8 declares done
- @microsoft/fetch-event-source maintenance status (last commit ~2 years ago) — confirm approach at Phase 7 plan time
- Railway request timeout for 120s+ protocol runs not applicable (Vercel is target) — verify Vercel function timeout limits before Phase 8

## Session Continuity

Last session: 2026-03-11T00:13:53.492Z
Stopped at: Completed 06-structured-output-and-reports/06-02-PLAN.md — awaiting human-verify checkpoint
Resume file: None
