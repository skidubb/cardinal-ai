# P26: Crazy Eights — Rapid Divergent Ideation with Dot Voting

## Overview

Crazy Eights is a design thinking protocol that forces rapid, uncensored ideation under extreme constraints, then uses democratic voting to surface the most promising concepts for development.

Each agent generates exactly 8 ideas (1-2 sentences each) with no self-editing. Ideas are clustered by theme, voted on (3 votes per agent, not for own ideas), and the top-voted concepts are developed into fuller proposals.

## Protocol Flow

```
Phase 1: Rapid Generation (Opus, parallel)
  Each agent → 8 ideas (1-2 sentences, no filtering)
      ↓
Phase 2: Cluster (Haiku)
  Pool all N×8 ideas → group by theme similarity
      ↓
Phase 3: Dot Vote (Haiku, parallel)
  Each agent → 3 votes (not own ideas)
      ↓
Phase 4: Develop Top Concepts (Opus)
  Top 3-5 voted ideas → full concept with rationale, risk, next step
```

## Usage

```bash
# Default (4 agents)
python -m protocols.p26_crazy_eights.run -q "How should we enter the European market?"

# All 7 agents (56 ideas total)
python -m protocols.p26_crazy_eights.run -q "What new product lines should we explore?" -a ceo cfo cto cmo coo cpo cro

# JSON output
python -m protocols.p26_crazy_eights.run -q "How do we reduce churn by 50%?" --json
```

## Output Structure

| Field | Type | Description |
|-------|------|-------------|
| `question` | str | The input question |
| `raw_ideas` | dict[str, list[str]] | Agent name → list of 8 ideas |
| `total_ideas` | int | Total ideas generated (agents × 8) |
| `clusters` | list[dict] | Themed groupings of ideas |
| `vote_tally` | dict[str, int] | Idea text → vote count |
| `top_ideas` | list[str] | Top 3-5 voted ideas |
| `developed_concepts` | list[dict] | Expanded concepts with rationale |
| `timings` | dict[str, float] | Per-phase timing in seconds |

## Design Decisions

- **Low max_tokens (2000) in Phase 1**: Enforces brevity — agents cannot over-explain ideas.
- **"Not your own" voting rule**: Prevents self-reinforcement bias and encourages cross-pollination.
- **Haiku for clustering and voting**: These are classification/selection tasks, not reasoning tasks.
- **Opus for generation and development**: Creative ideation and concept expansion benefit from stronger reasoning.
- **3-5 top ideas (with tie-breaking)**: Ensures at least 3 concepts are developed, includes ties up to 5.
