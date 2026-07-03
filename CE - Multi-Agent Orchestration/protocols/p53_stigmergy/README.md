# P53: Stigmergic Coordination

**Decentralized trace-field protocol — no central synthesizer.**

Agents deposit typed traces on shared "locations" over multiple waves. Later agents read the accumulated (and decayed) field and drop their own traces. The final output is the emergent trace field itself, mechanically grouped by type and ranked by cumulative strength. No LLM reads all outputs to "make sense" of the result.

| Property | Value |
|---|---|
| **Category** | Wave 2 Research |
| **Coordination** | **Decentralized** (mechanical harvest, no synthesizer) |
| **Problem Types** | Exploration, Systems Analysis, Multi-Stakeholder, General Analysis |
| **Agents** | 3–12 (recommended 5) |
| **Waves** | Default 3, max 6 |
| **Cost Tier** | Medium (N agents × W waves LLM calls, no synthesizer call) |

## Trace typology

Every trace has four fields:

| Field | Values | Purpose |
|---|---|---|
| `type` | `risk`, `opportunity`, `constraint`, `insight`, `question` | Guarantees coverage across problem-relevant dimensions |
| `location` | kebab-case topic facet (e.g. `unit-economics`, `regulatory-risk`) | Reused across agents to amplify convergence |
| `strength` | 0.3 (mild) / 0.6 (clear) / 0.9 (decision-critical) | Discretized so scoring stays interpretable |
| `content` | one sentence of specific analysis | The actual signal |

## How It Works

1. **Wave 1 — Seed.** Each agent (parallel) reads the question and drops 2–4 traces.
2. **Waves 2..N — React.** The current trace field (decayed by wave count) is rendered as a compact block. Each agent reads it and drops 2–4 new traces, either amplifying hot locations or seeding new ones. Decay factor is 0.6 per wave — a wave-1 trace is at ~0.22× its original strength by wave 3.
3. **Harvest — Mechanical.** Traces are grouped by `(type, location)`, cumulative decayed strength is computed, and the top-N locations per type are returned. **No LLM call.**

The result is the trace field, not a synthesizer's opinion.

## Why decentralized?

Most Cardinal Element protocols end in a central synthesizer (Opus reading every agent's output and writing a merged recommendation). That's centralized coordination: the synthesizer is the bottleneck and the decision-maker. P53 breaks the pattern:

- **No agent sees any specific other agent's contribution.** They read the accumulated (aggregated, decayed) field.
- **Convergence is measured, not decreed.** If three agents drop `risk`-type traces at `regulatory-risk`, its cumulative strength climbs. If nobody else visits a location, it drops out of the top-N report.
- **The final artifact isn't an opinion.** It's a ranked map of where the field concentrated. Consumers make the decision.

This puts P53 alongside P18 Delphi, P19 Vickrey, P20 Borda in the "Decentralized" bucket — but unlike those (which converge on a single answer via voting/auction/statistics), P53 is optimized for structured divergence.

## Usage

```bash
# 5 agents, 3 waves
python -m protocols.p53_stigmergy.run \
  --question "Should we enter the SEA market in 2027?" \
  --agents ceo cfo cto cmo cro

# Custom depth
python -m protocols.p53_stigmergy.run \
  --question "What breaks our GTM plan at 3× scale?" \
  --agents ceo cfo cro coo -w 4 --top-n 7

# JSON output
python -m protocols.p53_stigmergy.run \
  --question "..." \
  --agents ceo cfo cto \
  --json
```

## Arguments

| Arg | Default | Description |
|---|---|---|
| `-q, --question` | required | The question to explore |
| `-a, --agents` | ceo cfo cto cmo | Agent keys |
| `-w, --waves` | 3 | Number of trace waves |
| `--top-n` | 5 | Top locations per trace type in the final report |
| `--thinking-model` | claude-opus-4-6 | Model for agent trace deposits |
| `--json` | false | Emit raw JSON |

## Output structure

```json
{
  "question": "...",
  "waves": 3,
  "agents": ["CEO", "CFO", "CTO", "CMO", "CRO"],
  "all_traces": [
    {"trace_type": "risk", "location": "regulatory-risk", "strength": 0.9,
     "content": "GDPR export penalties can hit 4% of global revenue",
     "author": "CFO", "wave": 1}
  ],
  "by_type": {
    "risk": [
      {"location": "regulatory-risk", "trace_type": "risk",
       "cumulative_strength": 1.24, "trace_count": 3,
       "contributors": ["CFO", "CEO", "CRO"],
       "contents": ["...", "...", "..."]}
    ],
    "opportunity": [...],
    "constraint": [...],
    "insight": [...],
    "question": [...]
  }
}
```

## When to prefer / avoid

**Prefer** when the question rewards structured divergence more than convergence — mapping the problem landscape, surfacing what many independent perspectives agree matters (via emergent trace concentration), or exploring a poorly-scoped strategic question.

**Avoid** when the question demands one clean answer:
- Prioritization → use P19 Vickrey or P20 Borda
- Numerical estimation → use P18 Delphi or P32 Tetlock
- Root cause → use P16 ACH or P34 CRT
- Falsification → use P39 Popper

## Files

- `orchestrator.py` — 5-stage async class, mechanical harvest at the end
- `prompts.py` — reuses `prompt_fragments` for JSON envelope + prohibitions
- `capability.yaml` — router metadata
- `run.py` — CLI + `persist_run` (auto-score writes to `~/.coordination-lab/weights.json`)
