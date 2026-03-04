# P16: Analysis of Competing Hypotheses (ACH)

Generate hypotheses, score evidence for/against each, eliminate least supported.

| Attribute | Value |
|-----------|-------|
| **Category** | Intelligence Analysis |
| **Problem Type** | Diagnostic |
| **Tool Level** | T0 (no tools) |
| **Agents** | N analysts + 1 matrix coordinator |

## How It Works

1. **Phase 1 — Generate Hypotheses**: Each agent independently generates 2-3 plausible hypotheses (parallel, Opus).
2. **Phase 2 — List Evidence**: Hypotheses are deduplicated, then each agent identifies 3-5 relevant evidence items (parallel, Opus).
3. **Phase 3 — Build Matrix**: Each agent scores every evidence item against every hypothesis as Consistent (C), Inconsistent (I), or Neutral (N). Scores are aggregated via majority vote (parallel, Haiku).
4. **Phase 4 — Eliminate**: Hypotheses with the most Inconsistent evidence are eliminated. Key ACH principle: eliminate by inconsistency count, not confirmation count.
5. **Phase 5 — Sensitivity Analysis**: Identify the most diagnostic evidence, synthesize a final assessment with surviving hypotheses and confidence levels (Opus).

## Usage

```bash
python -m protocols.p16_ach.run \
  --question "Why is customer churn increasing despite product improvements?" \
  --agents ceo cfo cto cmo

# JSON output
python -m protocols.p16_ach.run \
  --question "What is causing the revenue shortfall in Q3?" \
  --agents ceo cfo cro \
  --json
```

## Output

- Ranked list of hypotheses with inconsistency counts
- Evidence-hypothesis matrix (C/I/N) aggregated across agents
- Diagnostic evidence ranking (which evidence best differentiates hypotheses)
- Final synthesis: conclusion, confidence level, key uncertainties, sensitivity notes

## Model Usage

| Phase | Model | Calls |
|-------|-------|-------|
| Generate Hypotheses | Opus | N agents |
| List Evidence | Opus | N agents |
| Build Matrix | Haiku | N agents x E evidence items |
| Sensitivity Synthesis | Opus | 1 |
