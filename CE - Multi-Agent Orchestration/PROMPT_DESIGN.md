# Prompt Design Philosophy — CE Multi-Agent Orchestration

This document describes the prompt engineering patterns used across the 48 coordination protocols. It is grounded in the actual prompt text and orchestrator code, not aspirational descriptions.

---

## 1. Adversarial Layering

Adversarial layering is the core mechanism for avoiding groupthink. Rather than asking agents to "consider multiple perspectives," the protocols structurally separate roles that are in tension with each other and enforce engagement between them.

### Three Patterns

**Pattern A — Dedicated role assignment (P17 Red/Blue/White Team)**

Each agent receives a hard-coded adversarial identity, not a suggestion to be balanced:

```
You are a RED TEAM analyst conducting adversarial stress-testing of a proposed plan.
...
Your job is to ATTACK this plan. Identify vulnerabilities, failure modes, blind spots,
hidden risks, flawed assumptions, and scenarios where this plan breaks down. Be thorough
and adversarial — your goal is to find every weakness before reality does.
```

The Blue Team then responds to the specific Red Team outputs — not to the plan in isolation:

```
You are a BLUE TEAM defender tasked with strengthening a proposed plan against identified attacks.
...
Address EVERY vulnerability listed above. If a vulnerability is genuinely undefendable,
say so honestly and propose a risk-acceptance rationale.
```

A White Team arbiter then adjudicates with an explicit anti-sycophancy instruction:

```
You must be impartial — neither reflexively siding with attackers nor defenders.
```

**Pattern B — Inversion of objective (P6 TRIZ)**

Rather than asking "how do we succeed?" the protocol inverts the goal:

```
You are participating in a TRIZ Inversion exercise. Your sole job is to
guarantee that the following plan or initiative FAILS spectacularly.
```

Failure mode categories are enumerated explicitly (operational, financial, market, technical, reputational, people) so agents cannot cluster around a single failure type. The INVERSION_PROMPT then mechanically converts each failure into its prevention:

```
For EACH failure mode, generate the specific mitigation or solution that would PREVENT that failure.
```

**Pattern C — Evidence-hypothesis independence (P16 ACH)**

ACH explicitly instructs evidence collection to focus on differentiation rather than confirmation:

```
Focus on evidence that helps DIFFERENTIATE between hypotheses rather than
evidence consistent with all of them.
```

The scoring matrix forces agents to mark each evidence item as Consistent, Inconsistent, or Neutral for each hypothesis independently. The synthesis prompt then requires concluding on "the hypothesis with the LEAST inconsistent evidence" — not the most consistent — which is the core ACH methodology for avoiding confirmation bias.

---

## 2. Cognitive Tier Mapping

Defined in `protocols/config.py`. Four tiers map to three models.

### The Tier Table

| Tier | Label | Model | Stage Types | Rationale |
|------|-------|-------|-------------|-----------|
| L1 | Pattern Match | `claude-haiku-4-5-20251001` | dedup, classify, extract, format, parse | Regex-equivalent reasoning; paying for Opus here is waste |
| L2 | Rule-Based | `claude-haiku-4-5-20251001` | score, rank, filter, vote, matrix | Explicit criteria application; no novel reasoning required |
| L3 | Analytical | `claude-sonnet-4-6` | assess, compare, analyze, evaluate | Structured comparison requires more than pattern matching |
| L4 | Creative/Strategic | `claude-opus-4-6` | synthesize, ideate, debate, reframe, generate, reason | Novel insight generation; where quality differences are largest |

The tier system is cited in the config as "inspired by CogRouter (arXiv:2602.12662)" — the academic framing for routing by cognitive load rather than by stage position.

### Configuration and Usage

```python
# protocols/config.py
COGNITIVE_TIERS = {
    "L1": ORCHESTRATION_MODEL,  # Haiku — fast pattern matching
    "L2": ORCHESTRATION_MODEL,  # Haiku — rule application
    "L3": BALANCED_MODEL,       # Sonnet — analytical reasoning
    "L4": THINKING_MODEL,       # Opus — creative/strategic synthesis
}

def model_for_stage(stage_type: str) -> str:
    level = STAGE_COGNITIVE_MAP.get(stage_type, "L4")  # Default to highest tier
    return COGNITIVE_TIERS[level]
```

The default fallback is L4 — if a stage type is unrecognized, use the most capable model. This means unknown stages never silently degrade.

### Think Fast and Slow Economics

The 40-60% cost reduction claim in the config comment comes from the distribution of stage types across a typical protocol run. In P48 Black Swan Detection (five layers), Layer 3 (Confluence Extraction) is a pure JSON extraction from structured text — it uses the orchestration model with no thinking budget. The four analytical/creative layers (Causal Graphs, Threshold Scans, Historical Analogues, Adversarial Memo) use Opus with full thinking budgets. The mechanical layer accounts for roughly 20% of stage count but a much smaller fraction of cost.

---

## 3. Emergence Detection

Emergence detection is not a single rubric embedded in one prompt — it is distributed across multiple synthesis prompts as a set of recurring analytical directives.

### What the Prompts Actually Require

The P48 CAUSAL_GRAPH_PROMPT contains the most explicit emergence instruction:

```
4. Emergence Analysis: Identify properties that appear in the INTERACTION
of subsystems but are NOT present in any individual subsystem. What behaviors
emerge only when these systems couple?
```

The P3 Parallel Synthesis protocol's SYNTHESIS_SYSTEM_PROMPT instructs the synthesizer to go beyond aggregation:

```
1. Identify areas of agreement across perspectives
2. Surface key tensions or trade-offs where perspectives diverge
3. Extract the strongest insights from each perspective
4. Produce a unified recommendation that integrates the best thinking
```

The structure enforces that the synthesizer must process disagreements as signal (step 2) before producing a recommendation (step 4). An aggregation-only model would skip step 2.

The P48 ADVERSARIAL_MEMO_PROMPT's confluence layer is the most operationalized emergence detector in the system. A confluence is defined as:

```
A CONFLUENCE is a scenario where 3 or more threshold variables activate
simultaneously or in rapid cascade. These are the conditions under which
black swan events emerge — not from single failures but from combinatorial
instability.
```

The CONFLUENCE_PROMPT (a mechanical L1/L2 stage) extracts these from threshold analysis outputs and requires:
- `trigger_sequence`: how one threshold breach cascades to others
- At minimum 3 variables per scenario

This operationalizes emergence as a JSON-extractable property rather than a subjective claim.

### The Analytical Prior Inversion in P48

The adversarial memo synthesis contains an explicit instruction to invert the analytical prior:

```
Your analytical prior is INVERTED from normal analysis: you are rewarded for
surfacing outliers, not penalized. Absence of evidence is not evidence of
absence. Improbable does not mean impossible.
```

This is the prompt-level equivalent of adjusting a prior probability — it directly instructs the model to weight toward novel findings rather than toward confident, mainstream conclusions.

---

## 4. Anti-Bias Guards

### Explicit Prohibition Language

P48 CAUSAL_GRAPH_PROMPT contains the strongest anti-bias guard in the codebase:

```
CRITICAL RULES:
- Single-cause explanations are PROHIBITED. Every outcome must trace through
  multiple causal paths.
- You must include at least 2 reinforcing loops and 2 balancing loops.
- Include cross-system interactions (e.g., how market dynamics interact with
  technology adoption, regulatory response, or social behavior).
```

The word "PROHIBITED" is the key pattern — it converts a heuristic ("try to include multiple causes") into a constraint violation. The minimum loop count requirement (2 reinforcing + 2 balancing) makes compliance measurable.

### Forced Alternative Generation

P16 ACH HYPOTHESIS_GENERATION_PROMPT requires hypotheses to be "mutually distinguishable" — not just multiple. The EVIDENCE_LISTING_PROMPT then repeats the differentiation constraint:

```
Focus on evidence that helps DIFFERENTIATE between hypotheses rather than
evidence consistent with all of them.
```

Evidence that is consistent with all hypotheses has zero diagnostic value in ACH — the prompt explicitly names this and redirects away from it.

### Evidence-Hypothesis Independence Scoring

The ACH matrix scoring is structured as three discrete states (C/I/N) rather than a continuous score:

```
- C (Consistent): the evidence supports or is expected under this hypothesis
- I (Inconsistent): the evidence contradicts or is unlikely under this hypothesis
- N (Neutral): the evidence neither supports nor contradicts this hypothesis
```

Requiring a discrete classification forces the agent to take a position on each evidence-hypothesis pair rather than hedging. The `reasoning` field is required alongside each score, which creates a trace for downstream sensitivity analysis.

### Historical Mechanism Matching (P48)

The HISTORICAL_ANALOGUE_PROMPT contains a surface-similarity guard:

```
Prioritize analogues where the MECHANISM of failure matches, not just surface
similarity. A financial crisis and an ecosystem collapse can share the same
cascade dynamics even if the domains differ.
```

This prevents the most common analogical reasoning failure: matching on domain labels rather than causal structure.

### Red Team Specificity Constraint (P17)

The Red Team prompt explicitly rejects vague risk identification:

```
Identify 3-5 vulnerabilities, prioritized by severity. Be specific and concrete —
vague risks are not useful.
```

Each vulnerability requires a `failure_scenario` field: "concrete scenario where this vulnerability causes plan failure." This prevents Red Team outputs from being lists of abstract categories rather than actionable findings.

---

## 5. Thinking Budget Allocation

Thinking budgets are set per orchestration phase, not per protocol. The OODA protocol (P40) is the clearest example of intra-protocol budget differentiation.

### P40 OODA Phase Budget Allocation

```python
# From protocols/p40_boyd_ooda/orchestrator.py

async def _observe(self, ...):
    compact_budget = 3000
    # "Speed over completeness. What are the 3 most important new facts?"

async def _orient(self, ...):
    # Uses self.thinking_budget (default: 10_000)
    # "The critical step" — mental model update

async def _decide(self, ...):
    compact_budget = 3000
    # "The single best action executable immediately"

async def _act(self, ...):
    compact_budget = 3000
    # "Project forward" — consequence mapping

async def _synthesize(self, ...):
    # Uses self.thinking_budget (default: 10_000)
    # Model evolution, final recommendation
```

The Orient phase gets full budget because the OODA framework itself designates it as "the critical step" — where situational analysis happens. The Observe, Decide, and Act phases get 3,000 tokens because their prompts are deliberately constrained ("3 most important facts," "single best action," "2-3 consequences").

### Stage-Type Budget Mapping

The stages.py module reveals how budget allocation works for the shared stage executors:

| Stage Type | Model | Thinking Budget | Example |
|------------|-------|-----------------|---------|
| `parallel_agent_stage` | thinking_model | `config["thinking_budget"]` (default 10K) | Creative, analytical |
| `sequential_agent_stage` | thinking_model | `config["thinking_budget"]` (default 10K) | Debate, iteration |
| `mechanical_stage` | orchestration_model | None (no thinking block) | Dedup, extraction |
| `synthesis_stage` | thinking_model | `config["thinking_budget"]` (default 10K) | Final synthesis |
| `multi_round_stage` | thinking_model | `config["thinking_budget"]` (default 10K) | Multi-round debate |

Mechanical stages explicitly do not send a `thinking` parameter to the API — they call `client.messages.create` without the thinking block at all. This is a hard boundary, not a soft budget reduction.

### P48 Layer Budget Mapping

| Layer | Stage Type | Model | Thinking Budget | Rationale |
|-------|------------|-------|-----------------|-----------|
| 1: Causal Graphs | `_parallel_agents` | Opus | 10K | Novel causal structure construction |
| 2: Threshold Scans | `_parallel_agents` | Opus | 10K | Phase transition identification |
| 3: Confluence Extraction | `_confluence_extract` | Haiku | None | JSON extraction from structured text |
| 4: Historical Analogues | `_parallel_agents` | Opus | 10K | Cross-domain analogical mapping |
| 5: Adversarial Memo | `_synthesize` | Opus | 10K | Final integration and framing |

Layer 3 is the only mechanical stage in P48 because confluence extraction is pattern matching on already-structured threshold data — the reasoning has already happened in Layer 2.

---

## Summary Table

| Design Pattern | Protocol(s) | Key Mechanism | Anti-Pattern It Prevents |
|----------------|-------------|---------------|--------------------------|
| Hard role assignment | P17 Red/Blue/White | `You are a RED TEAM analyst` — no hedging | Balanced-but-toothless analysis |
| Goal inversion | P6 TRIZ | "Your sole job is to guarantee failure" | Confirmation bias in risk assessment |
| Evidence-hypothesis independence | P16 ACH | C/I/N scoring matrix; differentiation constraint | Confirmation bias in evidence selection |
| Explicit prohibition | P48 Black Swan | "Single-cause explanations are PROHIBITED" | Monocausal narratives |
| Mechanism matching | P48 Black Swan | "Mechanism of failure matches, not surface similarity" | Domain-label analogical reasoning |
| Inverted analytical prior | P48 Black Swan | "Rewarded for surfacing outliers, not penalized" | Regression to mainstream consensus |
| Intra-protocol budget variation | P40 OODA | 3K for Observe/Decide/Act; 10K for Orient/Synthesis | Uniform cost for variable cognitive load |
| Cognitive tier routing | All protocols | L1-L4 → Haiku/Sonnet/Opus | Paying Opus rates for extraction tasks |
| Mechanical stage isolation | stages.py | No `thinking` block on orchestration model calls | Slow, expensive dedup and ranking |
| Specificity enforcement | P17, P6 | Required `failure_scenario` and `solution_description` fields | Abstract risk lists with no actionability |
