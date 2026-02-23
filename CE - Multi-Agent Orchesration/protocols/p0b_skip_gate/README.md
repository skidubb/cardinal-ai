# P0b: Cost-Aware Skip Gate

**Category:** Meta-Protocol
**Source:** AgentiQL (NeurIPS 2025)
**Agents:** 1 gate (Haiku) + 1 optional responder (Opus)

## Purpose

Decides whether a question warrants a full multi-agent pipeline or can be adequately answered by a single agent, balancing accuracy vs. compute cost.

## Phases

1. **Feature Extraction** (Haiku) — Extract complexity, ambiguity, risk, domain, stakes
2. **Gate Decision** (Haiku) — Skip (single agent) or escalate (multi-agent) based on feature thresholds
3. **Execute** — If skip: single Opus agent responds. If escalate: recommend protocol.

## Usage

```bash
python -m protocols.p0b_skip_gate.run --question "Should we expand into the EU market?"
python -m protocols.p0b_skip_gate.run --question "What's our Q3 revenue?" --json
```

## Key Insight

Not every problem needs a swarm. Simple, low-risk questions get fast answers at minimal cost.
