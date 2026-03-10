---
phase: 4
slug: agent-provider
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none — existing test infrastructure |
| **Quick run command** | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && python -m pytest tests/test_agent_provider.py -x` |
| **Full suite command** | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && python -m pytest tests/ -m "not integration" -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_agent_provider.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -m "not integration" -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | AGNT-01 | unit | `pytest tests/test_agent_provider.py::test_path_resolution -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | AGNT-01 | unit | `pytest tests/test_agent_provider.py::test_env_var_override -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | AGNT-02 | unit | `pytest tests/test_agent_provider.py::test_startup_assertion_fails -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | AGNT-02 | unit | `pytest tests/test_agent_provider.py::test_startup_assertion_passes -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 0 | AGNT-03 | unit | `pytest tests/test_agent_provider.py::test_default_mode_is_production -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 0 | AGNT-03 | unit | `pytest tests/test_agent_provider.py::test_research_mode_opt_in -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 0 | AGNT-03 | unit | `pytest tests/test_agent_provider.py::test_hard_failure_on_agent_failure -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_agent_provider.py` — stubs for AGNT-01, AGNT-02, AGNT-03 with mocked SdkAgent imports
- [ ] No additional conftest.py or framework install needed — existing infrastructure covers

*Existing test infrastructure (pytest 9.0.2) is already in place.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| API server starts in production mode with no manual path config | AGNT-02 | Requires running uvicorn with real Agent Builder installation | `cd "CE - Multi-Agent Orchestration" && uvicorn api.server:app --host 0.0.0.0 --port 8000` — verify log says "production mode" |
| CLI protocol run produces same output after path fix | AGNT-01 | Requires real API key and Agent Builder | `python -m protocols.p06_triz.run -q "test" -a ceo cfo cto` — verify output matches pre-change |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
