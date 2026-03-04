# P12: 25/10 Crowd Sourcing Protocol

**Rapid idea generation followed by blind scoring to surface top ideas.**

Category: Liberating Structures | Problem Type: Prioritization | Tool Level: T0

## How It Works

1. **Generate** — Each agent writes ONE bold idea on an anonymous "card" (parallel, Opus)
2. **Score** — Over N rounds, agents blindly score random cards they didn't author (parallel, Haiku)
   - Each card scored on: Boldness (1-5), Feasibility (1-5), Impact (1-5), Overall (1-5)
   - Agents don't know who wrote the card
   - Each agent scores a different random card each round
3. **Rank** — Ideas ranked by total score; top 25% highlighted
4. **Synthesize** — Strategic briefing with portfolio recommendation (Opus)

## Usage

```bash
# 7 agents, 5 scoring rounds (default)
python -m protocols.p12_twenty_five_ten.run \
  -q "Rank these initiatives for a bootstrapped AI consultancy with \$150K budget and 18 months runway: (a) hire senior consultant \$120K, (b) build self-serve PLG tool \$40K, (c) launch podcast \$15K, (d) attend 4 conferences \$50K, (e) proprietary training curriculum \$25K, (f) partner channel \$10K, (g) AI automation tools \$35K, (h) second geographic market \$20K" \
  --agents ceo cfo cto cmo coo cpo cro

# Custom rounds
python -m protocols.p12_twenty_five_ten.run -q "..." --rounds 3
```

## Output

`TwentyFiveTenResult` contains:
- `ideas` — Ranked list of `IdeaCard` objects with individual scores and scorer reactions
- `synthesis` — Strategic briefing with portfolio recommendation
- `scoring_rounds` / `total_scores_cast` — Scoring metadata

## Model Usage

| Stage | Model | Why |
|-------|-------|-----|
| Idea Generation | Opus 4.6 | Bold creative thinking needs depth |
| Blind Scoring | Haiku 4.5 | Fast structured evaluation (many parallel calls) |
| Synthesis | Opus 4.6 | Strategic analysis of scoring patterns |
