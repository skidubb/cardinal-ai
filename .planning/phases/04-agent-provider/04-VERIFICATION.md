---
phase: 04-agent-provider
verified: 2026-03-10T20:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
gaps: []
human_verification:
  - test: "Start API server with Agent Builder installed — observe startup log"
    expected: "Log line 'Production agent provider verified: SdkAgent importable from <path>'"
    why_human: "Requires a running FastAPI process with real Agent Builder; cannot verify log output without starting the server"
  - test: "Start API server with CE_AGENT_BUILDER_PATH=/nonexistent — observe crash"
    expected: "Server exits immediately with 'FATAL: Production agent import failed' before accepting requests"
    why_human: "Requires fresh environment where Agent Builder is absent; cannot simulate real ImportError in CI without venv restructuring"
  - test: "Run 'python -m protocols.p06_triz.run -q \"test question\" -a ceo cfo' end to end"
    expected: "Protocol completes with production SdkAgents — output format and quality match pre-change behavior"
    why_human: "Requires real ANTHROPIC_API_KEY and production agent instantiation; cannot be automated in CI"
---

# Phase 4: Agent Provider Hardening — Verification Report

**Phase Goal:** Harden the agent provider so production-mode SdkAgents load reliably, the API refuses to start if agent imports fail, and research mode requires explicit opt-in.
**Verified:** 2026-03-10T20:30:00Z
**Status:** PASSED
**Re-verification:** Yes — independent re-verification of previous `passed` report

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | API server refuses to start if SdkAgent cannot be imported | VERIFIED | `api/server.py` lines 28-44: lifespan hook raises RuntimeError with "FATAL: Production agent import failed" on ImportError |
| 2 | Default agent mode is 'production' everywhere — not 'research' | VERIFIED | `protocols/agent_provider.py` line 27: `_agent_mode: str = "production"` |
| 3 | Agent path resolves via CE_AGENT_BUILDER_PATH env var with computed fallback | VERIFIED | `_resolve_agent_builder_src()` lines 43-54: `os.environ.get("CE_AGENT_BUILDER_PATH")` checked first; falls back to `parents[2] / "CE - Agent Builder" / "src"` |
| 4 | If any agent fails to instantiate as SdkAgent, the entire run fails — no partial results | VERIFIED | `build_production_agents()` lines 125-153: `failed_agents` list collects all failures; RuntimeError raised after loop naming every failed agent |
| 5 | API runner uses build_production_agents() instead of DB-enriched thin dicts | VERIFIED | `runner.py` line 23: import; lines 228 and 554: both call sites replaced; `_resolve_agents()` retained with deprecation comment only |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `CE - Multi-Agent Orchestration/protocols/agent_provider.py` | Production-default provider with env var path, hard failure | VERIFIED | 156 lines, substantive. Line 27: `_agent_mode: str = "production"`. Contains `_resolve_agent_builder_src()`, `AgentBridge`, `build_production_agents()` with full hard-failure aggregation. |
| `CE - Multi-Agent Orchestration/api/server.py` | Startup assertion in lifespan hook | VERIFIED | Lines 28-44: full try/except block imports `_resolve_agent_builder_src` and `SdkAgent`, raises RuntimeError with actionable fix instructions on ImportError. |
| `CE - Multi-Agent Orchestration/api/runner.py` | Runner using build_production_agents | VERIFIED | Line 23 import confirmed. Lines 228 and 554 confirmed as call sites. `_resolve_agents()` retained at line 76 with deprecation docstring. |
| `CE - Multi-Agent Orchestration/tests/test_agent_provider.py` | Unit tests covering all 3 requirements | VERIFIED | 244 lines, 10 tests, all 10 passing (2.61s, no Agent Builder or API key needed). Covers AGNT-01 (5 tests), AGNT-02 (2 async tests), AGNT-03 (2 tests). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/server.py` | `csuite.agents.sdk_agent.SdkAgent` | import in lifespan hook | WIRED | Line 34: `from csuite.agents.sdk_agent import SdkAgent  # noqa: F401` inside lifespan try block |
| `api/runner.py` | `protocols/agent_provider.py` | build_production_agents import | WIRED | Line 23: `from protocols.agent_provider import build_production_agents`; used at lines 228 and 554 |
| `protocols/agent_provider.py` | `CE_AGENT_BUILDER_PATH` env var | `_resolve_agent_builder_src()` | WIRED | Line 49: `env_path = os.environ.get("CE_AGENT_BUILDER_PATH")`; returned via `Path(env_path).resolve()` on line 51 if set |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AGNT-01 | 04-01-PLAN.md | Agent provider uses absolute path (env var) instead of fragile sys.path.insert for SdkAgent imports; production mode is default; research requires explicit opt-in | SATISFIED | `_resolve_agent_builder_src()` with `CE_AGENT_BUILDER_PATH` override confirmed at line 49; `_agent_mode = "production"` at line 27; `set_agent_mode()` and `AGENT_MODE` env var are only opt-in paths. Tests `test_default_mode_is_production`, `test_path_resolution_env_var_override` pass. |
| AGNT-02 | 04-01-PLAN.md | API startup asserts SdkAgent import succeeds before accepting requests; fails loudly if production mode unavailable | SATISFIED | `server.py` lifespan hook lines 28-44 confirmed. RuntimeError message includes "FATAL", agent builder install instructions, and path fix option. Test `test_startup_assertion_fails_when_sdkagent_not_importable` passes. |
| AGNT-03 | 04-01-PLAN.md | Production mode is the default agent mode; research mode requires explicit opt-in | SATISFIED | `_agent_mode: str = "production"` at module level confirmed. Only `set_agent_mode("research")` or `AGENT_MODE=research` env var changes it. `build_production_agents()` raises RuntimeError on failure — no silent fallback to dicts. Tests `test_hard_failure_on_agent_failure` and `test_no_silent_fallback_to_research_mode` pass. |

No orphaned requirements. AGNT-01, AGNT-02, AGNT-03 are the only Phase 4 requirements in the REQUIREMENTS.md traceability table (lines 115-117), all marked Complete. All three are claimed in plan frontmatter and verified against the actual codebase.

### Anti-Patterns Found

None detected across all four phase-modified files.

Scanned for: `TODO`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER`, empty implementations (`return null`/`{}`/`[]`), silent fallback patterns, stub-only handlers, console.log-only functions.

The `_resolve_agents()` function in `runner.py` is intentionally retained with a deprecation docstring per plan specification — it is not called from any production path (both call sites use `build_production_agents()`).

### Regression Check

Full non-integration test suite: **164 passed, 0 failed, 37 xfailed** (118.5s). No regressions introduced.

Commits verified in git history:
- `992d90a` — test(04-01): add failing tests for agent provider hardening (RED phase)
- `cd95425` — feat(04-01): harden agent provider with production-default and hard failure (GREEN phase)

### Human Verification Required

The following items cannot be verified programmatically:

#### 1. API Server Startup Success

**Test:** From `CE - Multi-Agent Orchestration/`, with Agent Builder installed (`pip install -e '.[sdk]'`), run `uvicorn api.server:app`. Observe startup log.
**Expected:** Log line containing "Production agent provider verified: SdkAgent importable from" and the resolved path.
**Why human:** Requires a running FastAPI process with real Agent Builder present; cannot verify log output without starting the server.

#### 2. API Server Startup Failure Without Agent Builder

**Test:** In a clean environment without Agent Builder installed (or with `CE_AGENT_BUILDER_PATH=/nonexistent`), attempt to start the API server.
**Expected:** Server crashes immediately before accepting requests with "FATAL: Production agent import failed" and the two fix options listed.
**Why human:** Requires a fresh environment where Agent Builder is absent; cannot simulate real ImportError in CI without restructuring the venv.

#### 3. Production Protocol Run End to End

**Test:** Run `python -m protocols.p06_triz.run -q "Should we expand into Europe?" -a ceo cfo` in production mode.
**Expected:** Protocol completes with real SdkAgent instances — output format and quality match pre-change behavior.
**Why human:** Requires real `ANTHROPIC_API_KEY` and production agent instantiation; integration test cannot be automated in CI without live keys.

### Gaps Summary

No gaps. All five must-haves are fully satisfied against the actual codebase (not taken on trust from SUMMARY claims):

- `agent_provider.py` (156 lines) defaults to production mode, uses env-var-overridable path resolution, and raises RuntimeError naming every failed agent — no silent fallback exists in the code.
- `server.py` lifespan hook (lines 28-44) is wired: imports `_resolve_agent_builder_src` and `SdkAgent` inside a try/except and raises RuntimeError with "FATAL" prefix and actionable fix instructions on ImportError.
- `runner.py` imports `build_production_agents` at line 23 and calls it at both line 228 and line 554 — confirmed by direct grep.
- All 10 unit tests pass live (2.61s) without Agent Builder or API key.
- `.env.example` documents `CE_AGENT_BUILDER_PATH` with context at lines 69-71.
- Full non-integration suite (164 tests) passes — no regressions.

---

_Verified: 2026-03-10T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
