# P11: Discovery & Action Dialogue (DAD)

**Positive deviant identification: find who succeeds despite shared constraints, extract transferable practices.**

| Property | Value |
|---|---|
| **Category** | Liberating Structures |
| **Problem Type** | Exploration / Diagnostic |
| **Tool Level** | T0 (no tools) |
| **Agents** | N (any count) |

## How It Works

1. **Scout (Phase 1)** — Each agent independently identifies "positive deviants" from their role's perspective — specific examples of who or what succeeds despite facing the same constraints everyone else faces. Parallel, Opus with extended thinking. Each deviant includes the specific behavior and why it works.
2. **Filter (Phase 2)** — Each scouted behavior is tested against three criteria: (1) Is it genuinely uncommon? (2) Is it accessible/adoptable by others? (3) Is there evidence or causal logic for why it works? Behaviors that fail any criterion are discarded. Haiku, parallel per behavior.
3. **Extract (Phase 3)** — Surviving behaviors are analyzed to extract core transferable practices — the underlying principles stripped of context-specific details. Related behaviors are grouped into unified practices. Haiku.
4. **Adapt (Phase 4)** — Practices are synthesized into actionable recommendations adapted for the target context, with prioritization, adoption barriers, and implementation sequencing. Opus with extended thinking.

## Usage

```bash
# Default — 4 agents (CEO, CFO, CTO, CMO)
python -m protocols.p11_discovery_action_dialogue.run --question "Why do some startups thrive in this market while most fail?"

# All 7 agents for broader scouting
python -m protocols.p11_discovery_action_dialogue.run \
  --question "How can we reduce customer churn when competitors offer lower prices?" \
  --agents ceo cfo cto cmo coo cpo cro

# JSON output
python -m protocols.p11_discovery_action_dialogue.run \
  -q "What makes some engineering teams 10x more productive?" --json
```

## Output

The result includes all intermediate outputs for full lineage tracing:

- **Scouted deviants** — Each agent's identified positive deviants with behaviors and rationale
- **Filtered behaviors** — Behaviors that passed the uncommon/accessible/evidence filter, with reasoning
- **Extracted practices** — Core transferable practices derived from validated behaviors
- **Adapted recommendations** — Executive summary, ranked actions, adoption barriers, implementation sequence
- **Timings** — Elapsed time per phase

## Model Usage

| Phase | Model | Calls | Purpose |
|---|---|---|---|
| Scout | `claude-opus-4-6` | N | Identify positive deviants with extended thinking |
| Filter | `claude-haiku-4-5-20251001` | D (deviants found) | Test each behavior against 3 criteria |
| Extract | `claude-haiku-4-5-20251001` | 1 | Group and extract transferable practices |
| Adapt | `claude-opus-4-6` | 1 | Synthesize into adapted recommendations |
