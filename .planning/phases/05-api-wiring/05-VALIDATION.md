---
phase: 05
slug: api-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing in project) |
| **Config file** | none — pytest discovers tests/ directory |
| **Quick run command** | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && pytest tests/test_runs_api.py tests/test_protocols_api.py -x -q` |
| **Full suite command** | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && pytest tests/ -m "not integration" -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_runs_api.py tests/test_protocols_api.py -x -q`
- **After every plan wave:** Run `pytest tests/ -m "not integration" -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | API-01 | unit | `pytest tests/test_runs_api.py -k "test_protocol_run" -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | API-02 | unit | `pytest tests/test_runs_api.py -k "test_sse_headers" -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | API-10 | unit | `pytest tests/test_runs_api.py -k "test_disconnect_cancels" -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | API-09 | unit | `pytest tests/test_runs_api.py -k "test_context_var" -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | API-04 | unit | `pytest tests/test_runs_api.py -k "test_agents" -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | API-05 | unit | `pytest tests/test_runs_api.py -k "test_list_runs" -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | API-06 | unit | `pytest tests/test_runs_api.py -k "test_get_run" -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | API-07, API-08 | unit | `pytest tests/test_runs_api.py -k "test_pipeline" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_runs_api.py` — expand with endpoint tests via TestClient
- [ ] `tests/conftest.py` — shared TestClient fixture with in-memory SQLite DB override
- [ ] Ensure `httpx` installed (`pip install httpx`) for FastAPI TestClient

*Existing infrastructure covers API-03 (protocols list test exists).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE events visible in browser | API-02 | Requires browser/proxy layer | Open browser to /api/runs/{id}/stream, verify events arrive without buffering |
| Client disconnect stops API credits | API-10 | Requires real Anthropic API call | Start a protocol run, close browser tab, verify no further API charges |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
