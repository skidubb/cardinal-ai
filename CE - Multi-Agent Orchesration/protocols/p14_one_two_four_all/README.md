# P14: 1-2-4-All

**Progressive merging: solo ideation, pairs, quads, full-group synthesis.**

| Property | Value |
|---|---|
| **Category** | Liberating Structures |
| **Problem Type** | Exploration |
| **Tool Level** | T0 (no tools) |
| **Agents** | N (ideally power of 2; handles any count) |

## How It Works

1. **Solo (Stage 1)** — Each agent independently generates ideas from their role's perspective. All agents run in parallel using the thinking model (Opus).
2. **Pairs (Stage 2)** — Agents are paired. A fast merge model (Haiku) identifies shared themes, resolves tensions, and produces a single merged output per pair.
3. **Quads (Stage 3)** — Pair outputs are paired again. Haiku further refines and prioritizes, eliminating redundancy while preserving nuance.
4. **All (Stage 4)** — The thinking model (Opus) synthesizes all quad outputs into a final unified strategic response with executive summary, ranked recommendations, unresolved tensions, and next steps.

If an odd number of items exists at any merge stage, the leftover output carries forward to the next stage as-is.

## Usage

```bash
# Default — 4 agents (CEO, CFO, CTO, CMO)
python -m protocols.p14_one_two_four_all.run --question "Should we expand into the European market this year?"

# Custom agent set — 8 agents for clean power-of-2 merging
python -m protocols.p14_one_two_four_all.run \
  --question "How should we respond to the new competitor?" \
  --agents ceo cfo cto cmo coo cpo cro ceo

# Minimal — 2 agents (single pair, no quad stage)
python -m protocols.p14_one_two_four_all.run -q "What's our pricing strategy?" -a ceo cfo
```

## Output

The result includes all intermediate outputs for full lineage tracing:

- **Solo outputs** — Each agent's independent ideas
- **Pair outputs** — Merged themes from each pair
- **Quad outputs** — Refined and prioritized group positions
- **Final synthesis** — Executive summary, top recommendations, unresolved tensions, next steps
- **Stats** — Elapsed time and model call counts

## Model Usage

| Stage | Model | Calls | Purpose |
|---|---|---|---|
| Solo ideation | `claude-opus-4-6` | N | Independent idea generation with extended thinking |
| Pair merge | `claude-haiku-4-5-20251001` | N/2 | Find shared themes, resolve tensions |
| Quad merge | `claude-haiku-4-5-20251001` | N/4 | Refine and prioritize |
| Final synthesis | `claude-opus-4-6` | 1 | Unified strategic response with extended thinking |
