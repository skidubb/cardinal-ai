# P18: Delphi Method

Iterative expert estimation protocol with anonymous feedback and convergence detection.

## Protocol Logic

1. **Round 1 — Independent Estimates**: Each agent independently provides a numerical estimate with confidence interval and reasoning (parallel, Opus).
2. **Compute Stats**: Calculate median, interquartile range (IQR), and spread.
3. **Share & Re-estimate Loop**: Share anonymous group statistics (median, IQR) and all reasoning (without attribution) back to agents. Each agent revises their estimate. Repeat until convergence (IQR < 15% of median) or max rounds reached.
4. **Final Synthesis**: Haiku produces a summary of the consensus, key agreements/disagreements, and how estimates evolved.

## Usage

```bash
# Basic usage
python -m protocols.p18_delphi_method.run \
  -q "What percentage of enterprise SaaS companies will adopt AI agents by 2028?"

# Custom agents and rounds
python -m protocols.p18_delphi_method.run \
  -q "What will the average CAC payback period (in months) be for B2B SaaS in 2027?" \
  -a ceo cfo cmo cro \
  --max-rounds 5

# JSON output
python -m protocols.p18_delphi_method.run \
  -q "How many months until GPT-5 level models cost <$1/M tokens?" \
  --json
```

## Arguments

| Arg | Default | Description |
|-----|---------|-------------|
| `-q, --question` | required | Question requiring a numerical estimate |
| `-a, --agents` | ceo cfo cto cmo | Agent keys (available: ceo, cfo, cto, cmo, coo, cpo, cro) |
| `--max-rounds` | 3 | Maximum estimation rounds |
| `--thinking-model` | claude-opus-4-6 | Model for agent estimation |
| `--orchestration-model` | claude-haiku-4-5-20251001 | Model for final synthesis |
| `--json` | false | Output raw JSON |

## Convergence Criterion

The panel is considered converged when the interquartile range (IQR) is less than 15% of the median estimate. This threshold balances precision with practical convergence speed.

## Output Structure

```json
{
  "question": "...",
  "rounds": [
    {
      "round_number": 1,
      "estimates": [{"agent": "CEO", "estimate": 42.5, "confidence_low": 30, "confidence_high": 55, "reasoning": "..."}],
      "median": 40.0,
      "iqr": [35.0, 45.0],
      "spread": 10.0
    }
  ],
  "converged": true,
  "rounds_used": 2,
  "final_estimate": 41.0,
  "confidence_interval": [38.0, 44.0],
  "reasoning_summary": {"summary": "...", "key_agreements": [], "key_disagreements": [], "evolution_notes": "..."},
  "timings": {"round_1_estimates": 12.3, "round_2_estimates": 11.8, "synthesis": 2.1}
}
```
