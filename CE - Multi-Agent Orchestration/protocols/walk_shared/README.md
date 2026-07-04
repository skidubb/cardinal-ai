# LLM on a Walk — Protocol Family (P49-P52)

A cognitive exploration system that decomposes strategic questions through **14 orthogonal cognitive lenses**. Unlike decision-making protocols, Walk protocols are explicitly about *reframing* — they surface hidden assumptions, explore problem spaces, and discover what traditional expert consensus would miss.

## The 14 Cognitive Lenses

### Core Walkers (8)

| Key | Name | Lens Family | Core Transform |
|-----|------|-------------|----------------|
| `walk-framer` | Problem Framer | meta | Decomposition — breaks questions into assumptions, ambiguity, tensions |
| `walk-systems` | Systems Walker | systems | Feedback loop analysis — stocks, flows, delays, nonlinear dynamics |
| `walk-analogy` | Analogy Walker | analogical | Cross-domain mapping — biology, physics, military strategy, ecology |
| `walk-narrative` | Narrative Walker | narrative | Story structure analysis — hero/villain, privileged narratives, narrative traps |
| `walk-constraint` | Constraint Walker | constraint | Constraint mapping — real vs. assumed, binding constraints, removal experiments |
| `walk-adversarial` | Adversarial Walker | adversarial | Steelman opposition — fatal flaws, self-interest, opposite conclusions |
| `walk-salience-judge` | Salience Judge | meta | Salience scoring — novelty, explanatory power, actionability, cognitive distance |
| `walk-synthesizer` | Walk Synthesizer | meta | Multi-lens synthesis — convergent signal, genuine uncertainty, walk-unique insights |

### Distant Specialists (6)

These maximally orthogonal lenses increase cognitive distance from conventional analysis.

| Key | Name | Lens Family | Core Transform |
|-----|------|-------------|----------------|
| `walk-poet` | Poet | aesthetic | Metaphor extraction — compression, paradox, the unsaid |
| `walk-historian` | Historian | historical | Historical precedent — causal mechanisms, survivorship bias, false analogies |
| `walk-complexity` | Complexity Researcher | complexity | Complexity analysis — emergence, phase transitions, tipping points |
| `walk-semiotician` | Semiotician | semiotic | Sign analysis — signals, codes, second-order effects of description |
| `walk-economist` | Economist | economic | Incentive analysis — externalities, information asymmetry, value capture |
| `walk-statistician` | Statistician | statistical | Statistical reasoning — base rates, selection effects, regression to mean |

## The 6-Stage Pipeline

```
Stage 0: FRAME ──────────── Problem Framer decomposes the question
    │                       (Opus, single call)
    ▼
Stage 1: SHALLOW WALK ───── All 14 lenses reframe in parallel
    │                       (Balanced model, parallel)
    ▼
Stage 2: SALIENCE ────────── Judge scores all outputs, promotes top N
    │                       (Haiku, single call)
    ▼
Stage 3: DEEP WALK ──────── Only promoted lenses go deeper
    │                       (Opus, parallel)
    ▼
Stage 4: CROSS-EXAMINATION ─ Round-robin challenges between promoted
    │                       (Balanced model, parallel)
    ▼
Stage 5: SYNTHESIS ──────── Synthesizer integrates everything
                            (Opus + extended thinking)
```

### Stage Details

**Stage 0 — Frame**: The Problem Framer decomposes the question into objective, constraints, assumptions, dead ends, ambiguity map, and unresolved tensions. No solutions — only problem clarification.

**Stage 1 — Shallow Walk**: Every walker reframes the problem through its specific lens. Each produces: a reframe, a hidden variable, a blind spot, and a testable implication. All run in parallel.

**Stage 2 — Salience**: The Salience Judge scores every shallow output on four dimensions (1-10 each):
- **Novelty** (0.30 weight) — says something the obvious analysis misses
- **Explanatory power** (0.25) — accounts for more evidence than the default frame
- **Actionability** (0.25) — leads to concretely different decisions
- **Cognitive distance** (0.20) — how far from the default frame

Composite score determines promotion to deep walk.

**Stage 3 — Deep Walk**: Promoted lenses produce a thesis, critique of the incumbent frame, critique of another promoted lens, decision implications, disconfirming evidence, and a priority test.

**Stage 4 — Cross-Examination**: Round-robin pairings where each promoted lens challenges the next. Each produces: strongest opposing claim, settling evidence, and a concession.

**Stage 5 — Synthesis**: Integrates all stages into: best current interpretation, competing interpretations, walk-added value, decision changes, experiments, success signals, kill criteria, and what would change the view. Also produces a 2-4 paragraph prose synthesis.

## The 4 Variants

### P49: Walk Base — Reference Implementation

The full 6-stage pipeline. Balanced exploration with all stages active.

**When to use:** Default choice. Good for any strategic question where you want comprehensive multi-lens exploration.

```bash
python -m protocols.p49_walk_base.run \
  -q "Should we build an AI lab?" \
  --agents @walk \
  --promote-count 4
```

### P50: Tournament Walk — Cost-Optimized

Skips Stage 4 (cross-examination). Promotes only 3 lenses. ~40% cheaper than Walk Base.

**When to use:** Speed/cost-constrained situations. When you don't need lens-vs-lens debate.

```bash
python -m protocols.p50_tournament_walk.run \
  -q "Should we build an AI lab?" \
  --agents @walk \
  --promote-count 3
```

### P51: Wildcard Walk — Diversity-Preserving

Forces `include_wildcard=True` — the top 4 lenses plus one maximally orthogonal lens (highest cognitive distance outside the top 4). Full 6 stages.

**When to use:** When the risk is consensus blindness. Domains where outsider perspectives (poet, historian, complexity researcher) might see what insiders can't.

```bash
python -m protocols.p51_wildcard_walk.run \
  -q "Should we build an AI lab?" \
  --agents @walk
```

### P52: Drift-Return Walk — Serendipitous Exploration

The most creative variant. Overrides Stages 1 and 3 with custom prompts:

- **Stage 1 → Drift**: "FORGET THE QUESTION. Explore the domain. What is the most interesting, surprising, or underappreciated dynamic?" Agents explore the problem *space* abstractly, disconnected from the original framing.
- **Stage 3 → Return**: "You explored freely. Now RETURN to the question. Connect your drift insight back. Be explicit about what the drift revealed that directed analysis would have missed."

**When to use:** Novel questions where anchoring bias is the biggest risk. When you want serendipity and ponderous exploration over directed analysis.

```bash
python -m protocols.p52_drift_return_walk.run \
  -q "Should we build an AI lab?" \
  --agents @walk \
  --promote-count 4
```

## Variant Comparison

| Aspect | Base (P49) | Tournament (P50) | Wildcard (P51) | Drift-Return (P52) |
|--------|-----------|-------------------|----------------|---------------------|
| Stages | 6 | 5 (skip cross-exam) | 6 | 6 (modified 1 & 3) |
| Promoted lenses | Top 4 | Top 3 | Top 4 + 1 wildcard | Top 4 |
| Cross-exam | Yes | No | Yes | Yes |
| Relative cost | 100% | ~60% | ~110% | 100% |
| Emphasis | Balanced | Fast/cheap | Diversity | Serendipity |
| Shallow prompt | Standard reframe | Standard reframe | Standard reframe | Drift (free exploration) |
| Deep prompt | Standard thesis | Standard thesis | Standard thesis | Return (forced reconnection) |

## CLI Reference

All variants share the same CLI interface:

```
python -m protocols.p{49-52}_{variant}.run [OPTIONS]

Required:
  --question, -q          The strategic question to explore

Optional:
  --agents, -a            Agent names or @walk (default: @walk — all 14 lenses)
  --agent-config          Path to custom agent definitions JSON
  --thinking-model        Deep reasoning model (default: claude-opus-4-7)
  --orchestration-model   Mechanical/scoring model (default: claude-haiku-4-5-20251001)
  --thinking-budget       Extended thinking tokens (default: 10000)
  --promote-count         Lenses promoted to deep walk (default: 4, tournament: 3)
  --include-wildcard      Preserve one orthogonal wildcard (P49 only; P51 forces this)
  --trace                 Enable Langfuse tracing
  --trace-path            Save traces to file
  --dry-run               Print config and exit
  --mode                  research | production (default: production)
```

## Model Tiers

| Tier | Model | Used In |
|------|-------|---------|
| L4 (Thinking) | `claude-opus-4-7` | Frame (Stage 0), Deep Walk (Stage 3), Synthesis (Stage 5) |
| L3 (Balanced) | `claude-sonnet-4-6` | Shallow Walk (Stage 1), Cross-Exam (Stage 4) |
| L2 (Orchestration) | `claude-haiku-4-5-20251001` | Salience scoring (Stage 2) |

## Output Structure

All variants return a `WalkResult` containing:

```
WalkResult
├── question: str
├── protocol_variant: str
├── frame: FrameArtifact
│   ├── question, objective, constraints, assumptions
│   ├── known_dead_ends, ambiguity_map, unresolved_tensions
├── shallow_outputs: list[ShallowWalkOutput]
│   ├── agent_key, agent_name, lens_family
│   ├── reframe, hidden_variable, blind_spot, testable_implication
├── salience: SalienceArtifact
│   ├── ranked_outputs: list[SalienceScore]
│   │   ├── novelty, explanatory_power, actionability, cognitive_distance
│   │   ├── composite, rationale
│   ├── top_tensions, candidate_hypotheses, promoted_agents
├── deep_outputs: list[DeepWalkOutput]
│   ├── thesis, critique_of_incumbent_frame, critique_of_other_lens
│   ├── decision_implication, disconfirming_evidence, priority_test
├── cross_exam: list[CrossExamEntry]
│   ├── challenger_key, target_key
│   ├── strongest_opposing_claim, settling_evidence, concession
├── synthesis: WalkSynthesis
│   ├── best_current_interpretation, competing_interpretations
│   ├── walk_added_value, decision_changes, experiments
│   ├── success_signals, kill_criteria, what_would_change_view
└── synthesis_text: str (prose summary)
```

## File Structure

```
walk_shared/                    Shared infrastructure for all variants
├── agents.py                   14 cognitive lens definitions (WALK_AGENTS registry)
├── schemas.py                  Pydantic v2 models for all stage artifacts
├── prompts.py                  6 stage prompt templates
├── selection.py                Salience scoring, promotion logic, cross-exam pairings
└── README.md                   This file

p49_walk_base/                  Walk Base — reference implementation
├── orchestrator.py             WalkBaseOrchestrator (6 stages, all agent resolution)
├── prompts.py                  (uses walk_shared prompts directly)
└── run.py                      CLI entry point + print_result()

p50_tournament_walk/            Tournament — cost-optimized (skip cross-exam)
├── orchestrator.py             Extends WalkBase, overrides run() to skip Stage 4
├── prompts.py                  (uses walk_shared prompts)
└── run.py                      CLI entry point

p51_wildcard_walk/              Wildcard — diversity-preserving
├── orchestrator.py             Extends WalkBase, forces include_wildcard=True
├── prompts.py                  (uses walk_shared prompts)
└── run.py                      CLI entry point

p52_drift_return_walk/          Drift-Return — serendipitous exploration
├── orchestrator.py             Extends WalkBase, overrides Stages 1 & 3
├── prompts.py                  DRIFT_SHALLOW_PROMPT + RETURN_DEEP_PROMPT
└── run.py                      CLI entry point
```

## Design Philosophy

Walk protocols are **not decision-making tools**. They are cognitive exploration instruments. The key insight is that multi-agent systems can do something human experts struggle with: hold 14 genuinely different analytical frames simultaneously, score them for novelty rather than correctness, and synthesize across maximum cognitive distance.

The protocol deliberately separates *reframing* from *solutioning*. Stages 0-2 never try to answer the question — they only explore what the question really is. Stages 3-4 develop theses and challenge them. Only Stage 5 synthesizes toward action.

The salience scoring weights **novelty** highest (0.30) because the goal is to surface what conventional analysis would miss, not to confirm what we already believe.
