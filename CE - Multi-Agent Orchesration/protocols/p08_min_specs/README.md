# P08: Min Specs

**Identify the minimum set of rules needed to achieve a goal — nothing more.**

| Property | Value |
|---|---|
| **Category** | Liberating Structures |
| **Problem Type** | Constraint Definition |
| **Tool Level** | T0 (no tools) |
| **Agents** | N (any count; more agents = broader spec generation) |

## How It Works

1. **Generate Specs (Phase 1)** — Each agent independently generates ALL rules, constraints, and specifications they believe are necessary for the goal. All agents run in parallel using the thinking model (Opus with extended thinking).
2. **Union & Deduplicate (Phase 2)** — All specs are merged into a single list. The orchestration model (Haiku) deduplicates near-duplicates and subsumes overlapping specs, producing a canonical set.
3. **Elimination Test (Phase 3)** — For each spec, Haiku asks: "Would removing this make the purpose impossible?" Specs are classified as MUST_HAVE, REMOVABLE, or BORDERLINE. All tests run in parallel.
4. **Borderline Vote (Phase 4)** — For specs classified as borderline, every agent votes KEEP or REMOVE (parallel, Haiku). Majority wins.
5. **Final Synthesis (Phase 5)** — The thinking model (Opus) produces the definitive minimum specification set with rationale, eliminated specs for transparency, risks of going minimal, and implementation guidance.

## Usage

```bash
# Default — 4 agents (CEO, CFO, CTO, CMO)
python -m protocols.p08_min_specs.run --question "What are the minimum rules for launching a new product line?"

# All 7 agents for broader coverage
python -m protocols.p08_min_specs.run \
  --question "What are the non-negotiable constraints for our remote work policy?" \
  --agents ceo cfo cto cmo coo cpo cro

# JSON output for pipeline integration
python -m protocols.p08_min_specs.run \
  -q "What are the minimum specs for our data governance framework?" \
  --json
```

## Output

The result includes full lineage for transparency:

- **All specs** — The deduplicated union of everything agents proposed
- **Must-haves** — Specs that passed the elimination test (removing them = failure)
- **Eliminated** — Specs safely removed without compromising the goal
- **Borderline votes** — Per-agent votes on ambiguous specs with rationale
- **Final min specs** — The definitive minimum set (must-haves + borderline keeps)
- **Synthesis** — Executive summary, rationale per spec, risks, implementation guidance
- **Timings** — Per-phase elapsed time

## Model Usage

| Phase | Model | Calls | Purpose |
|---|---|---|---|
| Generate Specs | `claude-opus-4-6` | N | Independent spec generation with extended thinking |
| Deduplicate | `claude-haiku-4-5-20251001` | 1 | Merge and consolidate overlapping specs |
| Elimination Test | `claude-haiku-4-5-20251001` | S | Test each spec for essentiality (S = number of specs) |
| Borderline Vote | `claude-haiku-4-5-20251001` | B x N | Agents vote on borderline specs (B = borderline count) |
| Final Synthesis | `claude-opus-4-6` | 1 | Definitive min spec set with rationale |
