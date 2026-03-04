# Darwin Gödel Machine (DGM) × Coordination Lab: Analysis & Plan

## Context

Scott wants to make each protocol smarter using ideas from the Sakana AI Darwin Gödel Machine paper. The DGM is a self-improving coding agent that: (1) modifies its own code, (2) empirically validates changes on benchmarks, and (3) maintains an evolutionary archive of variants enabling open-ended exploration. Key result: SWE-bench 20% → 50%.

**The question**: How does this map to making our 48 coordination protocols self-improving?

## Strategic Analysis: DGM × Our Product

### What DGM Actually Does (and doesn't)

DGM evolves a **coding agent's tooling and workflow** — not its prompts. The mutations are things like "add patch validation and retry", "switch from full-file editing to string replacement", "auto-summarize on context limit". These are **structural/procedural improvements** to how the agent works, validated against an empirical benchmark.

### The Direct Analogy to Our Protocols

| DGM Concept | Our Equivalent |
|---|---|
| Coding agent codebase | Protocol `orchestrator.py` + `prompts.py` |
| Self-modification | LLM rewrites protocol prompts or orchestration logic |
| Benchmark (SWE-bench) | Our 7-dim judge + 12-criterion emergence rubric on 34 benchmark questions |
| Archive of variants | Version-tracked prompt/orchestrator variants per protocol |
| Open-ended exploration | Branch from any variant, not just the current best |
| Fitness function | Judge scores + emergence zone classification |

### Why This Is a Strong Fit

1. **We already have the fitness function.** The judge (`scripts/judge.py`) scores on 7 dimensions, the emergence detector (`scripts/emergence.py`) classifies into zones A-D. Most DGM-style systems need to build evaluation from scratch — we have it.

2. **Protocols are modular and isolated.** Each protocol is a self-contained `orchestrator.py` + `prompts.py`. Mutations to one protocol can't break others. This is the ideal search space structure.

3. **We have benchmark questions.** 34 structured questions across 8 problem types in `benchmark-questions.json`. This is our SWE-bench equivalent.

4. **The gap is the evolution loop.** We have evaluation-rich but evolution-poor infrastructure. No prompt versioning, no mutation engine, no selection, no feedback loop.

### What's Missing (Build Sequence)

| Component | Purpose | Priority |
|---|---|---|
| **Prompt Registry** | Version-track prompt variants per protocol (e.g., `p06_triz.synthesis_v1`, `v2`) | P0 — foundation |
| **Mutation Engine** | LLM generates prompt variants given current prompt + judge feedback | P0 — foundation |
| **Fitness History** | Link judge/emergence scores to specific prompt versions | P1 |
| **Selection Logic** | Pick top-scoring variants for breeding; support branching from any ancestor | P1 |
| **Evolution Runner** | Orchestrates: select parent → mutate → run benchmark → judge → archive | P2 |
| **Archive Visualization** | Tree view of variant lineage with performance coloring (like DGM Fig 3) | P3 |

### Product Positioning

This makes the Coordination Lab a **self-improving protocol research platform** — not just a library of fixed protocols. The pitch:

> "48 coordination protocols that get smarter every time they run. Each protocol evolves its prompts against empirical benchmarks, maintaining a lineage of variants. The best-performing variants are automatically selected and bred."

This is differentiated from every other multi-agent framework (CrewAI, AutoGen, LangGraph) which all have static prompts. It's also a natural extension of our existing evaluation infrastructure.

### Risks & Constraints

- **Cost**: DGM's SWE-bench run took 2 weeks of API costs. Our equivalent (48 protocols × N variants × 34 questions × judge calls) could be expensive. **Mitigation**: Start with 1-3 protocols, subset of questions, use Haiku for mutations.
- **Objective Hacking**: DGM found agents that removed detection mechanisms instead of solving problems. Our judge rubric is our defense — but we should monitor for prompts that game the rubric rather than genuinely improving. **Mitigation**: Human review of top-performing variants before promotion.
- **Search Space**: DGM mutates Python code. We'd be mutating prompts AND orchestration logic. Prompt mutations are safer and cheaper to evaluate. Start there. **Mitigation**: Phase 1 = prompt-only mutations. Phase 2 = orchestration logic mutations.

## Open Questions for Scott

1. **Mutation Target** — Should we evolve prompts only (safer, cheaper), orchestration logic (closer to DGM), or both?
2. **Archive Strategy** — Full DGM-style archive (keep all variants, branch from any ancestor) vs. Top-N tournament (simpler) vs. generational?
3. **Product Fit** — Research tool (offline evolution, human-curated promotion) vs. product feature (self-improving in production) vs. research now → product later?
4. **Budget** — Each iteration ≈ $5-15 (Opus thinking). Comfort level: minimal ($50-100 proof of concept), moderate ($200-500 real trends), or full ($500+)?
5. **Scope** — Which protocols first? P03, P04, P06, P17, P37 have the most emergence data for baseline comparison.

## Recommended Phase 1 Implementation

### Scope: Prompt Evolution Engine (prompt mutations only, 1-3 protocols)

Build the minimum viable evolution loop:

```
SELECT parent prompt variant
  → MUTATE (LLM generates new variant given parent + judge feedback)
  → EVALUATE (run protocol on benchmark subset)
  → JUDGE (score with existing judge/emergence rubric)
  → ARCHIVE (store variant + scores + lineage)
  → REPEAT
```

### Files to Create

All in `CE - Multi-Agent Orchestration/`:

#### 1. `evolution/prompt_registry.py`
- `PromptVariant` dataclass: `id`, `protocol_key`, `prompt_name`, `content`, `parent_id`, `generation`, `mutation_description`, `created_at`
- `PromptRegistry` class: CRUD on variants, stored as JSON files in `evolution/variants/{protocol_key}/`
- `get_active_variant(protocol_key, prompt_name) -> PromptVariant` — returns current best
- `get_lineage(variant_id) -> list[PromptVariant]` — ancestor chain

#### 2. `evolution/mutator.py`
- `mutate_prompt(current_prompt, judge_feedback, emergence_scores, mutation_strategy) -> str`
- Uses Sonnet (balanced model) to generate prompt variants
- Mutation strategies: `refine` (targeted fix based on lowest-scoring dimension), `explore` (creative rewrite preserving intent), `cross` (blend two parent variants)
- Includes the DGM insight: mutation instructions reference the specific judge dimensions that scored lowest

#### 3. `evolution/fitness.py`
- `evaluate_variant(protocol_key, prompt_name, variant_content, benchmark_subset) -> FitnessResult`
- Runs protocol with variant prompt on N benchmark questions
- Scores with judge + emergence detector
- Returns `FitnessResult`: per-question scores, aggregate, emergence zone distribution

#### 4. `evolution/archive.py`
- `Archive` class: manages the tree of variants
- Selection: weighted by fitness, with exploration bonus for under-explored branches (MAP-Elites style)
- Stores variant trees as JSON in `evolution/archives/{protocol_key}.json`

#### 5. `evolution/runner.py`
- CLI entry point: `python -m evolution.runner --protocol p06_triz --prompt SYNTHESIS_PROMPT --iterations 10 --benchmark-subset Q1.1,Q1.2,Q1.3`
- Orchestrates the full loop: select → mutate → evaluate → judge → archive
- Progress reporting and cost tracking

#### 6. `evolution/__init__.py`
- Exports

### Key Design Decisions

1. **Prompt-only mutations first.** Don't touch orchestrator logic in Phase 1. Prompts are the highest-leverage, lowest-risk mutation target.
2. **JSON file storage.** No new database dependency. Variant trees are small enough for JSON.
3. **Subset evaluation.** Don't run all 34 questions. Start with 3-5 questions per problem type the protocol targets.
4. **Sonnet for mutations.** Opus for judging (existing), Sonnet for generating variants (cost balance).
5. **Human-in-the-loop promotion.** Top variants get flagged for human review before replacing the default prompt.

### Reference Files

| File | Purpose |
|---|---|
| `scripts/judge.py` | Existing 7-dim judge — reuse as fitness function |
| `scripts/emergence.py` | Existing 12-criterion emergence rubric — reuse for zone classification |
| `scripts/evaluate.py` | Existing evaluation harness — model for running protocols on benchmarks |
| `benchmark-questions.json` | 34 benchmark questions — the evaluation corpus |
| `protocols/config.py` | Model constants |
| `protocols/p06_triz/prompts.py` | Example protocol prompts — first mutation target |

### Verification

1. `python -m evolution.runner --protocol p06_triz --prompt SYNTHESIS_PROMPT --iterations 3 --benchmark-subset Q1.1` — runs 3 evolution iterations
2. Check `evolution/variants/p06_triz/` — variant JSON files created with lineage
3. Check `evolution/archives/p06_triz.json` — archive tree with fitness scores
4. `ruff check evolution/` — no lint errors
5. Manual review: compare v1 vs best variant output quality on same question
