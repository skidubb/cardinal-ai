---
phase: 6
slug: structured-output-and-reports
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (Python) / vitest (React) |
| **Config file** | pyproject.toml (Python) / ui/vitest.config.ts (React) |
| **Quick run command** | `pytest tests/test_protocol_report.py -x` |
| **Full suite command** | `pytest tests/ -m 'not integration' -x && cd ui && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_protocol_report.py -x`
- **After every plan wave:** Run `pytest tests/ -m 'not integration' -x && cd ui && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | OUT-01 | unit | `pytest tests/test_protocol_report.py::test_protocol_report_fields -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | OUT-02 | unit | `pytest tests/test_protocol_report.py::test_from_envelope -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | OUT-05 | unit | `pytest tests/test_protocol_report.py::test_confidence_label -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | OUT-06 | unit | `pytest tests/test_protocol_report.py::test_agent_contributions -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | REPT-01 | unit | `pytest tests/test_reports_api.py::test_pdf_endpoint -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | REPT-02 | smoke | `pytest tests/test_reports_api.py::test_pdf_content_smoke -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | REPT-03 | unit | `pytest tests/test_reports_api.py::test_share_url_no_auth -x` | ❌ W0 | ⬜ pending |
| 06-02-04 | 02 | 2 | OUT-03 | unit | `cd ui && npx vitest run src/__tests__/ProtocolReport.test.tsx` | ❌ W0 | ⬜ pending |
| 06-02-05 | 02 | 2 | OUT-04 | unit | included in ProtocolReport.test.tsx | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_protocol_report.py` — stubs for OUT-01, OUT-02, OUT-05, OUT-06
- [ ] `tests/test_reports_api.py` — stubs for REPT-01, REPT-02, REPT-03
- [ ] `ui/src/__tests__/ProtocolReport.test.tsx` — stubs for OUT-03, OUT-04
- [ ] WeasyPrint smoke test: `python -c 'import weasyprint; weasyprint.HTML(string="<p>ok</p>").write_pdf()'`
- [ ] `api/templates/report.html.j2` — Jinja2 template file (Wave 0 asset)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF visual quality | REPT-02 | Layout/typography judgment | Open generated PDF, verify headings, sections, CE branding are readable |
| Disagreement visual distinction | OUT-04 | Color/border visual check | View run with disagreements in browser, verify amber/distinct styling |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
