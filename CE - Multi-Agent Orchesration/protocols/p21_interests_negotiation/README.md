# P21: Interests-Based Negotiation

**Category:** Game Theory
**Protocol Family:** Negotiation & Conflict Resolution

## Overview

Interests-Based Negotiation (IBN) moves beyond positional bargaining to surface underlying interests, map shared/compatible/conflicting needs, and generate mutual-gains options. The protocol finds Pareto-optimal agreements where no agent is made worse off.

## Protocol Flow

```
Phase 1: Surface Interests (parallel, Opus)
    Each agent identifies underlying needs, fears, aspirations
        ↓
Phase 2: Interest Map (Haiku mediator)
    Categorize all interests as shared / compatible / conflicting
        ↓
Phase 3: Generate Options (parallel, Opus)
    Each agent brainstorms options satisfying multiple interests
        ↓
Phase 4: Evaluate & Select (Haiku scoring + Pareto check)
    Score options against all agents' interests
    If no Pareto-optimal option → repeat Phase 3-4
        ↓
Phase 5: Synthesize Agreement (Opus)
    Combine best options into coherent agreement
```

## Usage

```bash
# Basic usage
python -m protocols.p21_interests_negotiation.run \
  -q "How should we allocate the $2M budget between engineering, marketing, and operations?"

# With specific agents and max rounds
python -m protocols.p21_interests_negotiation.run \
  -q "Should we pursue the acquisition of CompetitorX?" \
  -a ceo cfo cto cmo \
  --max-rounds 3

# JSON output
python -m protocols.p21_interests_negotiation.run \
  -q "How to handle the pricing restructure?" \
  --json
```

## Key Design Decisions

- **Interests, not positions**: Agents surface WHY they want something, not WHAT they demand
- **Mediator pattern**: Haiku acts as neutral categorizer, preventing any agent from framing the interest map
- **Pareto-optimality**: Options are only selected if no agent is made worse off; if none found, another round of creative option generation runs
- **Multi-round option generation**: Up to `--max-rounds` attempts to find mutual-gains solutions before settling

## Output Structure

| Field | Description |
|---|---|
| `interest_maps` | Per-agent list of underlying interests with priority and type |
| `categorized_interests` | Shared, compatible, and conflicting interest buckets |
| `generated_options` | All proposed mutual-gains options |
| `option_scores` | Per-option, per-agent satisfaction scores |
| `selected_agreement` | Final synthesized agreement with key terms and trade-offs |
| `interest_satisfaction` | Dict of agent name to satisfaction score (0.0-1.0) |
| `timings` | Per-phase execution times |
