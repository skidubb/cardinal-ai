# P20: Borda Count Voting

**Ranked-choice voting with Borda scoring across multiple agents.**

| Property | Value |
|---|---|
| **Category** | Game Theory |
| **Problem Type** | Prioritization / Ranking |
| **Tool Level** | T0 (no tools) |
| **Agents** | N (odd counts recommended for cleaner tiebreaks) |

## How It Works

1. **Rank (Phase 1)** — Each agent independently ranks ALL options from best to worst, providing reasoning for each position. All agents run in parallel using the thinking model (Opus).
2. **Score (Phase 2)** — Borda points are assigned: 1st place gets K-1 points, 2nd gets K-2, down to 0 for last place (K = number of options). Points are summed per option across all agents. Pure computation, no API call.
3. **Analyze (Phase 3)** — Check for ties. If options are tied on Borda score, Condorcet head-to-head comparison is used: for each pair of tied options, count how many agents ranked A above B. The option winning more pairwise matchups ranks higher. Haiku produces tiebreak analysis if needed.
4. **Report (Phase 4)** — Opus produces the final report: full ranking with scores, reasoning clusters (common themes across agents per option), consensus analysis, margin of victory, and dissenting views.

## Usage

```bash
# Default — 5 agents rank 3 options
python -m protocols.p20_borda_count.run \
  --question "Which market should we enter next?" \
  --options "Europe" "Southeast Asia" "Latin America"

# Custom agents, more options
python -m protocols.p20_borda_count.run \
  -q "What should be our top product investment?" \
  -o "AI features" "Mobile app" "Enterprise tier" "API platform" \
  -a ceo cfo cto cpo cro

# JSON output
python -m protocols.p20_borda_count.run \
  -q "Which pricing model?" \
  -o "Freemium" "Usage-based" "Flat-rate" \
  --json
```

## Output

The result includes full lineage for audit and analysis:

- **Ballots** — Each agent's complete ranking with per-position reasoning
- **Borda scores** — Total points per option across all agents
- **Final ranking** — Options sorted by score (with tiebreaks resolved)
- **Winner** — Top-ranked option
- **Margin** — Point gap between 1st and 2nd place
- **Tiebreak flag** — Whether Condorcet comparison was needed
- **Reasoning clusters** — Common arguments grouped by option
- **Consensus score** — 0.0 (total disagreement) to 1.0 (unanimous)
- **Report** — Full narrative for decision-makers

## Model Usage

| Phase | Model | Calls | Purpose |
|---|---|---|---|
| Rank | `claude-opus-4-6` | N | Independent ranking with extended thinking |
| Score | (computation) | 0 | Sum Borda points |
| Analyze | `claude-haiku-4-5-20251001` | 0-1 | Tiebreak analysis (only if ties exist) |
| Report | `claude-opus-4-6` | 1 | Final synthesis and reasoning clusters |

## Scoring Example

With 4 options and 3 agents:
- 1st place = 3 pts, 2nd = 2 pts, 3rd = 1 pt, 4th = 0 pts
- Maximum possible score per option = 3 agents x 3 pts = 9
- Minimum possible score = 0
