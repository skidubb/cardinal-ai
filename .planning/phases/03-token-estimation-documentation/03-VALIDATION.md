---
phase: 3
slug: token-estimation-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | ce-shared/pyproject.toml (existing) |
| **Quick run command** | `cd ce-shared && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd ce-shared && python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd ce-shared && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd ce-shared && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | TOKN-01 | unit | `pytest tests/test_pricing.py -k estimate` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | TOKN-04 | unit | `pytest tests/test_pricing.py -k unknown_model` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | TOKN-05 | unit | `pytest tests/test_cost_tracker.py -k ceiling` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | TOKN-06 | unit | `pytest tests/test_cost_tracker.py -k env_ceiling` | ❌ W0 | ⬜ pending |
| TBD | 03 | 2 | TOKN-02 | integration | manual — requires SDK agent | N/A | ⬜ pending |
| TBD | 03 | 2 | TOKN-03 | integration | manual — requires Langfuse | N/A | ⬜ pending |
| TBD | 04 | 2 | DOCS-01 | manual | `test -f "CE - Agent Builder/docs/BYPASS_PERMISSIONS.md"` | ❌ W0 | ⬜ pending |
| TBD | 04 | 2 | DOCS-02 | manual | `test -f ce-shared/README.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `ce-shared/tests/test_pricing.py` — add tests for `estimate_tokens_from_cost()` (TOKN-01, TOKN-04)
- [ ] `ce-shared/tests/test_cost_ceiling.py` — tests for budget guardrail (TOKN-05, TOKN-06)

*Existing test infrastructure in ce-shared covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Production agent path records estimated tokens | TOKN-02 | Requires SDK agent + protocol run | Run a protocol with a production agent, check Langfuse trace |
| Langfuse traces show non-zero tokens | TOKN-03 | Requires Langfuse connection | Run protocol, check Langfuse UI for generation spans |
| BYPASS_PERMISSIONS.md content quality | DOCS-01 | Content review | Read doc, verify it covers what/where/why/risks/mitigations |
| ce-shared README accuracy | DOCS-02 | Content review | Verify import examples work |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
