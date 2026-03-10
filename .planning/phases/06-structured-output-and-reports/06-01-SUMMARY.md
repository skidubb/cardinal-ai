---
phase: 06-structured-output-and-reports
plan: 01
subsystem: api
tags: [dataclass, protocol-report, structured-output, run-envelope, judge-verdict, sqlite]

# Dependency graph
requires:
  - phase: 05-api-wiring
    provides: runner.py SSE pipeline, GET /api/runs/{id} endpoint, AgentOutput/Run models
provides:
  - ProtocolReport dataclass with from_envelope() transform (protocols/protocol_report.py)
  - build_envelope_from_db() reconstructing RunEnvelope from DB rows (api/report_helpers.py)
  - judge_verdict_json column on Run table for persistence
  - protocol_report field in GET /api/runs/{id} response
affects: [07-report-viewer-ui, 08-pdf-export-shareable-url]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ProtocolReport is a pure dataclass in protocols/ with no api/ dependency — presentation independence"
    - "from_envelope() is the single transform boundary between RunEnvelope and ProtocolReport"
    - "build_envelope_from_db() reconstructs RunEnvelope from SQLite rows for report regeneration"
    - "judge_verdict_json stored as JSON string TEXT column on Run table"

key-files:
  created:
    - CE - Multi-Agent Orchestration/protocols/protocol_report.py
    - CE - Multi-Agent Orchestration/api/report_helpers.py
    - CE - Multi-Agent Orchestration/tests/test_protocol_report.py
  modified:
    - CE - Multi-Agent Orchestration/api/models.py
    - CE - Multi-Agent Orchestration/api/runner.py
    - CE - Multi-Agent Orchestration/api/routers/runs.py

key-decisions:
  - "ProtocolReport lives in protocols/ not api/ — no circular dependency, UI layer is in api/"
  - "confidence_label_str field name avoids conflict with confidence_label() function"
  - "protocol_report only added for status=completed runs — pending/failed runs return null"
  - "pre-existing test_full_pipeline_mocked flakiness is timing-related, unrelated to this plan"

patterns-established:
  - "from_envelope pattern: every RunEnvelope can be transformed to ProtocolReport in one call"
  - "extract_disagreements capped at 4: prevents overwhelming UI with noise"
  - "Internal agent keys (_synthesis, _result, _stage) excluded from contributions consistently"

requirements-completed: [OUT-01, OUT-02, OUT-05, OUT-06]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 06 Plan 01: Structured Output Foundation Summary

**ProtocolReport dataclass with from_envelope() transform, judge_verdict_json DB persistence, and protocol_report field wired into GET /api/runs/{id} response**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-10T20:12:01Z
- **Completed:** 2026-03-10T20:18:44Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created ProtocolReport + AgentContribution dataclasses with all 9 required fields and as_dict() serialization
- Implemented from_envelope() transform mapping any RunEnvelope to ProtocolReport in one call
- Added disagreement extraction (7 signal words, capped at 4), key findings extraction (bullet/sentence fallback), and confidence label mapping (0=Unscored, 1-2=Low, 3=Medium, 4-5=High)
- Added judge_verdict_json TEXT column to Run model for verdict persistence
- Created build_envelope_from_db() to reconstruct RunEnvelope from SQLite for report regeneration
- Wired protocol_report into GET /api/runs/{id} response for completed runs
- 22 unit tests all passing (TDD)

## Task Commits

Each task was committed atomically:

1. **Task 1: ProtocolReport dataclass, from_envelope transform, and unit tests** - `9c7042b` (feat)
2. **Task 2: Persist judge_verdict_json, add build_envelope_from_db, wire protocol_report into GET runs/{id}** - `e44722e` (feat)

_Note: Task 1 used TDD — tests written first (RED), then implementation (GREEN)_

## Files Created/Modified
- `CE - Multi-Agent Orchestration/protocols/protocol_report.py` - ProtocolReport + AgentContribution dataclasses, from_envelope(), extract_disagreements(), extract_key_findings(), confidence_label()
- `CE - Multi-Agent Orchestration/tests/test_protocol_report.py` - 22 unit tests covering all behaviors
- `CE - Multi-Agent Orchestration/api/models.py` - Added judge_verdict_json TEXT field to Run
- `CE - Multi-Agent Orchestration/api/runner.py` - Persist judge_verdict_dict to run.judge_verdict_json after evaluation
- `CE - Multi-Agent Orchestration/api/report_helpers.py` - build_envelope_from_db() reconstructing RunEnvelope from DB rows
- `CE - Multi-Agent Orchestration/api/routers/runs.py` - protocol_report field in GET /api/runs/{id} response

## Decisions Made
- ProtocolReport lives in protocols/ (not api/) to avoid circular dependency — the UI/presentation layer lives in api/, so report data must be in protocols/
- Used confidence_label_str as the dataclass field name to avoid collision with the confidence_label() helper function
- protocol_report is only populated when run.status == "completed" — pending/failed runs return null to avoid incomplete data
- Pre-existing test_full_pipeline_mocked flakiness is a timing issue unrelated to this plan (passes in isolation)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- None

## User Setup Required
None — schema change requires deleting orchestrator.db before restarting the server (documented in models.py comment). SQLite does not auto-add columns to existing tables.

## Next Phase Readiness
- ProtocolReport data layer complete and tested — ready for Phase 07 browser UI rendering
- GET /api/runs/{id} returns protocol_report for all completed runs
- build_envelope_from_db() available for any component needing to regenerate reports from DB
- No blockers

---
*Phase: 06-structured-output-and-reports*
*Completed: 2026-03-10*
