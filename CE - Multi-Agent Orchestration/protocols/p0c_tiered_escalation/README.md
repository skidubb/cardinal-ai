# P0c: Tiered Escalation

**Category:** Meta-Protocol
**Source:** TAO — Tiered Adaptive Oversight
**Agents:** 1 per tier (Tier 1) → N parallel (Tier 2) → N debate + 1 oversight (Tier 3)

## Purpose

Routes queries to the simplest adequate tier first. If confidence is low or errors detected, escalates to progressively more rigorous protocols.

## Tiers

1. **Tier 1: Fast Agent** — Single Opus response. Haiku evaluates confidence. If >= threshold → done.
2. **Tier 2: Multi-Agent Synthesis** — Parallel Opus agents. Haiku synthesizes and scores consensus. If >= threshold → done.
3. **Tier 3: Full Consensus** — Agents write rebuttals after seeing others' work. Haiku oversight reviews for safety. If fails → flag for human.

## Usage

```bash
python -m protocols.p0c_tiered_escalation.run --question "Should we acquire CompetitorX?"
python -m protocols.p0c_tiered_escalation.run -q "..." --confidence-threshold 90 --consensus-threshold 0.8
python -m protocols.p0c_tiered_escalation.run -q "..." --agents '[{"name":"CEO","system_prompt":"..."}]' --json
```

## Key Insight

Router errors are caught by escalation triggers. Tier 1 is efficient but risky alone; Tier 3 is safe but expensive — used only when needed.
