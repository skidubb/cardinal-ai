# P19: Vickrey Auction — Second-Price Sealed-Bid Option Selection

Agents place sealed bids on the best option; winner is calibrated to the second-highest confidence to prevent overconfidence.

| Attribute | Value |
|-----------|-------|
| **Category** | Game Theory |
| **Problem Type** | Prioritization / Selection |
| **Tool Level** | T0 (no tools) |
| **Agents** | N bidders + 1 synthesizer |

## How It Works

1. **Phase 1 — Sealed Bidding**: Each agent independently evaluates all options, selects their top choice, and assigns a confidence score (0-100). Bids are sealed — no agent sees another's choice (parallel, Opus).
2. **Phase 2 — Reveal & Rank**: All bids are revealed simultaneously. Agents are ranked by confidence. The highest-confidence bidder wins; the second-highest confidence becomes the "price."
3. **Phase 3 — Calibrated Justification**: The winning agent must justify their choice at the SECOND-highest confidence level, not their own. This Vickrey mechanism prevents overconfidence and encourages truthful bidding (Opus).
4. **Phase 4 — Final Assessment**: Synthesize the winning recommendation, calibrated confidence, bid distribution across options, and consensus analysis (Haiku).

## Why Vickrey?

In a standard Vickrey auction, the winner pays the second-highest price, which incentivizes truthful bidding. Applied to multi-agent option selection:
- Agents have no incentive to inflate confidence (overconfidence gets corrected down to the second price)
- The gap between first and second confidence reveals how differentiated the winning option truly is
- Consensus score shows whether agents converged or diverged across options

## Usage

```bash
python -m protocols.p19_vickrey_auction.run \
  --question "Which market should we enter next?" \
  --options "Southeast Asia" "Latin America" "Eastern Europe" \
  --agents ceo cfo cto cmo

# JSON output
python -m protocols.p19_vickrey_auction.run \
  --question "Which pricing model should we adopt?" \
  --options "Usage-based" "Per-seat" "Flat-rate" "Freemium" \
  --agents ceo cfo cro cpo \
  --json
```

## Output

- All sealed bids with agent, selected option, confidence, and reasoning
- Winning agent and option with original and second-price confidence
- Calibrated justification (hedged to second-price confidence level)
- Bid distribution: which options attracted how many bids at what confidence
- Consensus score (0.0-1.0): degree of agent convergence

## Model Usage

| Phase | Model | Calls |
|-------|-------|-------|
| Sealed Bidding | Opus | N agents |
| Reveal & Rank | — (local computation) | 0 |
| Calibrated Justification | Opus | 1 |
| Final Assessment | Haiku | 1 |
