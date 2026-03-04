# P0a: Reasoning Router

**Meta-protocol** — Classifies a strategic question and recommends the optimal coordination protocol. Does **not** execute the selected protocol; execution is left to the caller.

## How It Works

| Phase | Model | Description |
|-------|-------|-------------|
| 1. Feature Extraction | Haiku | Extracts structural features: complexity, ambiguity, risk, domain, stakeholders, time horizon, evidence/creativity needs, conflict |
| 2. Problem Type Classification | Haiku | Maps features to one of 10 problem types (Diagnostic, Exploration, Adversarial, etc.) |
| 3. Protocol Selection | Haiku | Selects optimal protocol based on problem type and cost considerations |
| 4. Assembly | — | Packages result with alternatives, reasoning, and cost tier |

## Protocol Mapping

| Problem Type | Primary Protocol(s) |
|---|---|
| Diagnostic | P16 ACH, P23 Cynefin |
| Exploration | P14 1-2-4-All, P6 TRIZ, P26 Crazy Eights |
| Adversarial | P17 Red/Blue/White Team |
| Prioritization | P20 Borda Count, P19 Vickrey Auction |
| Estimation | P18 Delphi Method |
| Constraint Definition | P8 Min Specs |
| Multi-Stakeholder | P10 HSR, P21 Interests Negotiation, P9 Troika |
| Portfolio Management | P13 Ecocycle Planning |
| Systems Analysis | P24 Causal Loop, P25 System Archetype |
| General Analysis | P15 What/So What/Now What, P22 Sequential Pipeline |
| Simple/Low-Risk | P3 Parallel Synthesis, P1 Single Agent |

## Usage

```bash
# Pretty-printed output
python -m protocols.p0a_reasoning_router.run -q "Why are our enterprise customers churning at 2x the rate of SMBs?"

# JSON output
python -m protocols.p0a_reasoning_router.run -q "Should we build or buy a data pipeline?" --json
```

## Output

- `question` — The input question
- `features` — Extracted structural features (complexity, ambiguity, risk, etc.)
- `problem_type` — Classified problem type with confidence
- `recommended_protocol` — Primary protocol recommendation
- `alternatives` — Alternative protocols with reasons to prefer each
- `reasoning` — Explanation of the routing decision
- `cost_tier` — "low", "medium", or "high"
- `timings` — Phase-level timing breakdown
