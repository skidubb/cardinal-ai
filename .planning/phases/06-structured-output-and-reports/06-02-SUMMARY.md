---
phase: 06-structured-output-and-reports
plan: 02
subsystem: ui
tags: [react, jinja2, weasyprint, pdf, html-report, tailwind, vitest, testing-library]

# Dependency graph
requires:
  - phase: 06-structured-output-and-reports/06-01
    provides: ProtocolReport dataclass, from_envelope() transform, protocol_report in GET /api/runs/{id}
provides:
  - Jinja2 report.html.j2 template for PDF and shareable HTML rendering
  - GET /api/reports/{run_id}/pdf endpoint with WeasyPrint PDF generation
  - GET /share/{run_id} public HTML route (no auth required)
  - React ProtocolReport component with disagreement highlighting and confidence dots
  - useRunStream protocolReport state — fetched from API after run completion
  - 25 vitest tests covering all ProtocolReport component behaviors
affects: [07-report-viewer-ui, 08-pdf-export-shareable-url]

# Tech tracking
tech-stack:
  added: [weasyprint, jinja2, react-markdown, remark-gfm]
  patterns:
    - "ProtocolReport React component with data-testid attributes for all sections — enables reliable E2E testing"
    - "Confidence score rendered as 5 dots with color coding (green 4-5, yellow 3, red 1-2, gray 0) — never raw number"
    - "Amber border-l-4 + bg-amber-50 for disagreements — visually distinct from all other sections"
    - "Agent cards collapsed by default, expand on click via useState — reduces cognitive overload on initial view"
    - "useRunStream fetches GET /api/runs/{id} after run_complete event to get protocol_report — decoupled from SSE stream"
    - "/share/{run_id} excluded from auth middleware before API key check — public shareable reports"

key-files:
  created:
    - CE - Multi-Agent Orchestration/api/templates/report.html.j2
    - CE - Multi-Agent Orchestration/api/routers/reports.py
    - CE - Multi-Agent Orchestration/tests/test_reports_api.py
    - CE - Multi-Agent Orchestration/ui/src/components/ProtocolReport.tsx
    - CE - Multi-Agent Orchestration/ui/src/__tests__/ProtocolReport.test.tsx
  modified:
    - CE - Multi-Agent Orchestration/api/server.py
    - CE - Multi-Agent Orchestration/ui/src/pages/RunView.tsx
    - CE - Multi-Agent Orchestration/ui/src/hooks/useRunStream.ts

key-decisions:
  - "asyncio.to_thread() for WeasyPrint write_pdf() — avoids blocking FastAPI event loop during PDF generation"
  - "WeasyPrint failure returns 501 with actionable error message — not a hard 500"
  - "protocolReport fetched separately after SSE run_complete event — avoids complicating SSE stream format"
  - "Share Report link in RunView only shown when stream.runId is available — prevents broken links"

patterns-established:
  - "Report rendering via Jinja2 template used for both PDF (WeasyPrint) and HTML (FastAPI HTMLResponse) — single source of truth"
  - "data-testid attributes on all major report sections — enables both unit tests and future E2E tests"

requirements-completed: [OUT-03, OUT-04, OUT-05, OUT-06, REPT-01, REPT-02, REPT-03]

# Metrics
duration: 8min
completed: 2026-03-10
---

# Phase 06 Plan 02: Presentation Layer Summary

**Jinja2 PDF/HTML report template, WeasyPrint PDF endpoint, public /share/ route, and React ProtocolReport component with amber disagreement highlighting and 5-dot confidence indicator**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-10T20:30:00Z
- **Completed:** 2026-03-10T21:05:00Z
- **Tasks:** 2 automated (Task 3 is checkpoint:human-verify, awaiting visual confirmation)
- **Files modified:** 8

## Accomplishments
- Created Jinja2 report.html.j2 template with all report sections, professional inline styling, self-contained for both PDF and HTML rendering
- Implemented GET /api/reports/{run_id}/pdf endpoint using WeasyPrint with asyncio.to_thread() to avoid blocking — graceful 501 with actionable error if WeasyPrint system deps missing
- Implemented GET /share/{run_id} public HTML route excluded from auth middleware
- Created React ProtocolReport component with confidence dots (green/yellow/red/gray by score), amber-bordered disagreements section, expandable agent cards with react-markdown rendering
- Wired ProtocolReport into RunView and useRunStream — protocol_report fetched after run completion, Share Report link links to /share/{run_id}
- 25 vitest tests covering all component behaviors

## Task Commits

Each task was committed atomically:

1. **Task 1: Jinja2 report template, PDF endpoint, shareable HTML route, and API tests** - `95a14b0` (feat)
2. **Task 2: React ProtocolReport component with disagreement highlighting and confidence indicator** - `720d9e4` (feat)

_Note: Task 3 is a human-verify checkpoint — awaiting visual confirmation_

## Files Created/Modified
- `CE - Multi-Agent Orchestration/api/templates/report.html.j2` - Jinja2 template for PDF and shareable HTML, self-contained inline CSS
- `CE - Multi-Agent Orchestration/api/routers/reports.py` - PDF endpoint and shareable HTML route with WeasyPrint integration
- `CE - Multi-Agent Orchestration/api/server.py` - Registered reports router, excluded /share/ from auth middleware
- `CE - Multi-Agent Orchestration/tests/test_reports_api.py` - API tests for PDF endpoint, shareable URL, and auth exclusion
- `CE - Multi-Agent Orchestration/ui/src/components/ProtocolReport.tsx` - React component with all sections and data-testid attributes
- `CE - Multi-Agent Orchestration/ui/src/__tests__/ProtocolReport.test.tsx` - 25 vitest tests
- `CE - Multi-Agent Orchestration/ui/src/pages/RunView.tsx` - Renders ProtocolReport when available, adds Share Report link
- `CE - Multi-Agent Orchestration/ui/src/hooks/useRunStream.ts` - Added protocolReport state, fetches from API after completion

## Decisions Made
- Used asyncio.to_thread() for WeasyPrint to avoid blocking the FastAPI event loop — PDF generation is CPU-bound
- WeasyPrint unavailability returns 501 with actionable brew/pip install instructions rather than 500
- protocolReport is fetched in a separate GET /api/runs/{id} call after the SSE run_complete event — keeps SSE stream format clean
- /share/{run_id} auth exclusion placed before API key validation so the check applies regardless of SKIP_AUTH setting

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- Task 2 files (ProtocolReport.tsx, RunView.tsx, useRunStream.ts, test file) existed as uncommitted changes from a prior session; verified all 25 tests pass and committed them under this plan's Task 2 commit.

## User Setup Required
WeasyPrint requires system libraries for PDF generation:
- macOS: `brew install pango`
- Linux: `apt-get install libpango1.0-dev libcairo2-dev`
- If unavailable, GET /api/reports/{run_id}/pdf returns 501 with installation instructions

## Next Phase Readiness
- Complete report presentation layer: PDF download, shareable URL, browser component all implemented
- Awaiting Task 3 human-verify checkpoint to confirm visual quality
- After confirmation: phase 06 is complete, ready for phase 07 or 08

---
*Phase: 06-structured-output-and-reports*
*Completed: 2026-03-10*
