---
phase: 2
slug: environment-consolidation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | ce-shared/pyproject.toml `[tool.pytest]` |
| **Quick run command** | `cd ce-shared && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd ce-shared && python -m pytest tests/ -v && cd "../CE - Agent Builder" && python -m pytest tests/ -m "not integration" -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd ce-shared && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ENVR-01 | unit | `pytest ce-shared/tests/test_env.py -k find_and_load` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ENVR-02 | unit | `pytest ce-shared/tests/test_env.py -k registry` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | ENVR-03 | unit | `pytest ce-shared/tests/test_env.py -k validation` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | ENVR-04 | integration | `docker compose config --quiet` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | ENVR-05 | unit | `pytest ce-shared/tests/test_env.py -k cwd_loads_root` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | ENVR-06 | unit | `pytest ce-shared/tests/test_env.py -k missing_required_fails` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 3 | ENVR-07 | unit | `pytest ce-shared/tests/test_env_check.py` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 3 | ENVR-08 | manual | `python -m ce_shared.env_check` | N/A | ⬜ pending |
| 02-05-01 | 05 | 3 | ENVR-09 | integration | `find . -name ".env" -not -path "./.env" -not -path "*/venv/*"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `ce-shared/tests/test_env.py` — stubs for ENVR-01 through ENVR-06
- [ ] `ce-shared/tests/test_env_check.py` — stubs for ENVR-07
- [ ] `ce-shared/tests/conftest.py` — fixtures for temp .env files, monkeypatched env vars

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| env_check Rich output formatting | ENVR-08 | Terminal-dependent color rendering | Run `python -m ce_shared.env_check` and visually confirm grouped output with color-coded status |
| Docker compose runs with interpolated vars | ENVR-04 | Requires running Docker daemon | Run `docker compose up -d postgres` and verify connection |

*All other behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
