---
created: 2026-03-09T23:32:55.505Z
title: Add shared protocol output report layer
area: general
files:
  - CE - Multi-Agent Orchestration/protocols/synthesis.py
  - CE - Multi-Agent Orchestration/protocols/run_envelope.py
  - CE - Multi-Agent Orchestration/api/runner.py
  - CE - Agent Builder/src/csuite/formatters/dual_output.py
  - CE - Agent Builder/src/csuite/formatters/audit_formatter.py
---

## Problem

Protocol runs produce good synthesis content but wrap it in inconsistent, developer-oriented formatting. Each protocol owns its own `print_result()` function with raw terminal output (70-char separator bars, text dumps). There is no shared report template that gives users a clear, scannable summary answering: "What did the agents do? Where did they disagree? What's the recommendation? How confident should I be?"

Key gaps:
- No executive-readable deliverable format — output is developer terminal text, not a polished summary
- No consistent narrative structure across protocols (which agents participated, disagreements, what got surfaced vs filtered, confidence levels)
- CE - Agent Builder has better formatting (Rich panels, branded markdown via AuditFormatter, DualArtifact) but this doesn't flow back to protocol runs
- RunEnvelope normalizes for persistence but not for human-readable presentation
- SynthesisEngine generates the content but there's no presentation layer on top

## Solution

1. Design a shared `ProtocolReport` output format that all protocols can use — structured sections (participants, key findings, disagreements, synthesis, confidence, metadata)
2. Consider borrowing patterns from Agent Builder's `AuditFormatter` and `DualArtifact` for branded markdown output
3. Build a `ReportRenderer` that can output to multiple targets (terminal/Rich, markdown file, HTML, API JSON)
4. Retrofit existing `print_result()` functions to use the shared layer
5. Ensure the report structure supports both quick-scan (executive summary) and deep-dive (full agent outputs, reasoning traces)
