# P24: Causal Loop Mapping

**Category:** Systems Thinking
**Protocol Family:** Feedback structure analysis

## Overview

Causal Loop Mapping is a systems thinking method that identifies feedback loops driving system behavior. Multiple agents extract system variables, identify causal relationships, and the orchestrator computationally traces reinforcing and balancing feedback loops before analyzing leverage points for intervention.

## Phases

| Phase | Description | Model | Parallelism |
|-------|-------------|-------|-------------|
| 1. Extract Variables | Each agent identifies key system variables | Opus | Parallel |
| 2. Deduplicate | Merge and deduplicate variables into canonical set | Haiku | Single |
| 3. Identify Causal Links | Each agent identifies A→B relationships with polarity | Opus | Parallel |
| 4. Merge & Trace Loops | Majority-vote polarity, DFS cycle detection | Computation | N/A |
| 5. Leverage Analysis | Identify highest-impact intervention points | Opus | Single |

## Key Concepts

- **Polarity (+/-)**: "+" means same-direction effect (A up → B up). "-" means opposite-direction (A up → B down).
- **Reinforcing Loop**: All polarities positive, or even number of negative — amplifies change (virtuous/vicious cycle).
- **Balancing Loop**: Odd number of negative polarities — resists change (stabilizing feedback).
- **Leverage Point**: A variable where intervention produces outsized systemic effect.

## Usage

```bash
python -m protocols.p24_causal_loop_mapping.run \
  -q "Why is our engineering team struggling to ship features on time?" \
  -a ceo cto coo cpo

# JSON output
python -m protocols.p24_causal_loop_mapping.run \
  -q "What systemic factors drive customer churn in our SaaS product?" \
  --json
```

## Output Structure

```
{
  "question": "...",
  "variables": [{"id": "V1", "name": "...", "description": "..."}],
  "causal_links": [{"from": "V1", "to": "V3", "polarity": "+", "reasoning": "..."}],
  "reinforcing_loops": [{"id": "R1", "path": ["V1", "V3", "V5"], "polarities": ["+", "+", "+"]}],
  "balancing_loops": [{"id": "B1", "path": ["V2", "V4", "V6"], "polarities": ["+", "-", "+"]}],
  "leverage_points": {...},
  "timings": {...}
}
```
