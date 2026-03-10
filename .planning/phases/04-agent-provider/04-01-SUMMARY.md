---
phase: 04-agent-provider
plan: 01
subsystem: api
tags: [agent-provider, sdk-agent, fastapi, production-mode, testing, mocking]

# Dependency graph
requires: []
provides:
  - Production-default agent provider with env var path resolution and hard failure on instantiation error
  - FastAPI lifespan startup assertion that refuses to start if SdkAgent is not importable
  - runner.py using build_production_agents() at both protocol and pipeline call sites
  - 10 unit tests covering all 3 requirements (runnable without Agent Builder installed)
affects: [05-protocol-run-api, 06-orchestration-ui, 07-sse-streaming]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_resolve_agent_builder_src() function with CE_AGENT_BUILDER_PATH env var override"
    - "Hard failure pattern: collect all failed agents, raise RuntimeError listing names — no silent fallback"
    - "Lifespan startup assertion: import SdkAgent in lifespan hook, raise RuntimeError with actionable message if unavailable"
    - "TDD execution: RED (tests fail) committed first, then GREEN (implementation) committed"

key-files:
  created:
    - CE - Multi-Agent Orchestration/tests/test_agent_provider.py
  modified:
    - CE - Multi-Agent Orchestration/protocols/agent_provider.py
    - CE - Multi-Agent Orchestration/api/server.py
    - CE - Multi-Agent Orchestration/api/runner.py
    - .env.example

key-decisions:
  - "Production is the default agent mode — research mode requires explicit opt-in via set_agent_mode() or AGENT_MODE env var"
  - "Hard failure on ANY agent instantiation error: all agents must load as SdkAgent, no partial results"
  - "CE_AGENT_BUILDER_PATH env var overrides computed sibling-directory path — enables Docker and non-standard layouts"
  - "_resolve_agents() in runner.py retained but deprecated — build_production_agents() used at both call sites"

patterns-established:
  - "Hard failure aggregation: collect (key, error) tuples across all agents, raise single RuntimeError listing all failures"
  - "Startup import assertion: verify critical imports in lifespan hook with actionable fix instructions in error message"

requirements-completed: [AGNT-01, AGNT-02, AGNT-03]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 4 Plan 1: Agent Provider Hardening Summary

**Production-default SdkAgent provider with env-var path resolution, hard failure on instantiation errors, and FastAPI startup assertion that refuses to start without Agent Builder**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T18:38:31Z
- **Completed:** 2026-03-10T18:44:09Z
- **Tasks:** 2 (TDD: 1 RED commit + 1 GREEN commit)
- **Files modified:** 5

## Accomplishments

- Eliminated silent degradation: `_agent_mode` now defaults to `"production"` — research mode requires explicit opt-in
- Added `_resolve_agent_builder_src()` with `CE_AGENT_BUILDER_PATH` env var override for non-standard Agent Builder locations
- Replaced per-agent silent fallback with hard `RuntimeError` that lists all failed agent names — no partial results
- Added startup assertion in FastAPI lifespan hook: server refuses to start if SdkAgent is not importable, with actionable fix instructions
- Replaced both `_resolve_agents()` call sites in `runner.py` with `build_production_agents()`
- 10 unit tests covering all 3 requirements, runnable without Agent Builder installed or `ANTHROPIC_API_KEY` set

## Task Commits

Each task was committed atomically:

1. **Task 1: Write unit tests for agent provider hardening** - `992d90a` (test)
2. **Task 2: Harden agent provider, startup assertion, and runner integration** - `cd95425` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD task has 2 commits — RED (test) then GREEN (implementation)_

## Files Created/Modified

- `CE - Multi-Agent Orchestration/tests/test_agent_provider.py` — 10 unit tests covering AGNT-01/02/03 using mocked SdkAgent
- `CE - Multi-Agent Orchestration/protocols/agent_provider.py` — Production default, `_resolve_agent_builder_src()`, hard failure
- `CE - Multi-Agent Orchestration/api/server.py` — Startup assertion in lifespan hook with actionable error message
- `CE - Multi-Agent Orchestration/api/runner.py` — `build_production_agents()` at both call sites; `_resolve_agents()` deprecated
- `.env.example` — `CE_AGENT_BUILDER_PATH` documented in Agent Provider section

## Decisions Made

- Production is the default agent mode — any code that wants research mode must explicitly call `set_agent_mode("research")` or set `AGENT_MODE=research`
- Hard failure aggregation pattern: collect all `(key, error)` tuples in the loop, raise a single `RuntimeError` naming every failed agent — forces operator awareness, prevents silent degradation
- `CE_AGENT_BUILDER_PATH` env var overrides the computed sibling-directory path — enables Docker deployments and non-standard repo layouts
- `_resolve_agents()` function in `runner.py` retained with deprecation comment (not deleted) as plan specified — may be referenced from external tooling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. `CE_AGENT_BUILDER_PATH` is optional and only needed for non-standard Agent Builder locations.

## Next Phase Readiness

- Agent provider is hardened and production-ready
- Any code that previously relied on silent fallback to research mode will now fail loudly with actionable error messages
- `CE_AGENT_BUILDER_PATH` env var provides operational flexibility for Docker/Vercel deployments
- Full non-integration test suite passes with 164 tests, 0 failures

---
*Phase: 04-agent-provider*
*Completed: 2026-03-10*
