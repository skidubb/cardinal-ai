# CE AGENTS: From Protocol Library to Coordination Learning System

## Engineering Spec for Claude Code Implementation

---

## Core Thesis

Progress comes not from adding more intelligent parts, but from discovering a better compression layer that makes many parts legible, governable, and generative at once.

**First era:** design the moves.
**Second era:** design the game.

---

## Strategic Reframe

CE AGENTS currently operates as an **authored protocol library**: 64 protocols, 24 agents, 7 academic traditions, manually orchestrated. This spec defines the migration path toward a **coordination learning system** that discovers, evaluates, and refines its own coordination patterns through structured experience.

The 64 protocols are not the core IP. They are the first expansion layer. The actual compression underneath them is: **different problem types require different cognitive coordination structures.** Everything built next should deepen that compression, not widen the catalog.

---

## Three Compression Levels

All engineering work maps to one of these. Label every feature, ticket, and design decision accordingly.

### Level 1: Procedural Compression
The system learns recurring workflow patterns: when to parallelize, when to debate, when to retrieve first, when to synthesize first, when to escalate, when to stop.

**Status:** Partially built. Most current protocols live here.
**Near-term value:** High.

### Level 2: Representational Compression
The system learns better internal encodings of problem types. Not "use protocol 7 for market analysis" but "these seemingly different tasks share the same latent structure: ambiguous goals, noisy evidence, asymmetric downside, need for adversarial challenge."

**Status:** Not yet instrumented.
**Near-term value:** High. This is where routing gets smart.

### Level 3: Conceptual Compression
The system identifies simpler principles governing broader classes of observations. Actual theory formation. Paradigm-level.

**Status:** Aspirational.
**Near-term value:** Low. Do not optimize here yet. Do not use this language in sales.

---

## Coordination Primitives

Replace the protocol catalog mental model with a **compositional grammar**. Protocols become compositions of primitives. Compositions become learnable.

### Candidate Primitive Set

```
decompose    - break problem into subproblems
propose      - generate candidate solutions or framings
challenge    - adversarial evaluation of proposals
retrieve     - pull relevant context, precedent, evidence
simulate     - model outcomes under assumptions
score        - evaluate against explicit criteria
reconcile    - resolve conflicts between competing outputs
escalate     - flag uncertainty or constraint violations for human review
compress     - synthesize outputs into minimal coherent form
```

### Implementation Tasks

- [ ] Define primitive interface: each primitive is a callable unit with typed input/output, cost estimate, and trace metadata
- [ ] Map existing 64 protocols to primitive compositions: express each protocol as an ordered/branching sequence of primitives
- [ ] Identify redundancy: which protocols are identical or near-identical at the primitive level?
- [ ] Identify gaps: which useful primitive compositions have no corresponding protocol?
- [ ] Store compositions as data, not code: primitive sequences should be JSON/YAML representations that the system can read, mutate, and store

### Falsification Test
If the primitive set cannot express at least 80% of existing protocols as compositions, the primitives are wrong. Revise until they can.

---

## Problem Typing and Latent Structure

The system needs a taxonomy of problem types based on structural features, not surface domains.

### Candidate Dimensions for Problem Typing

```yaml
goal_clarity:        [clear, ambiguous, contradictory]
evidence_quality:    [rich, sparse, noisy, adversarial]
downside_symmetry:   [symmetric, asymmetric_negative, asymmetric_positive]
time_pressure:       [unbounded, constrained, urgent]
stakeholder_count:   [single, few, many, adversarial]
domain_familiarity:  [well_known, partially_known, novel]
output_type:         [decision, analysis, artifact, recommendation, plan]
evaluation_clarity:  [objective_metric, subjective_judgment, no_clear_eval]
decomposability:     [naturally_modular, entangled, sequential]
```

### Implementation Tasks

- [ ] Build a `ProblemProfile` schema based on these dimensions
- [ ] Create a classifier (LLM-based initially) that infers a ProblemProfile from task description and context
- [ ] Log ProblemProfile alongside every run in Langfuse
- [ ] Build routing logic that maps ProblemProfile regions to primitive compositions
- [ ] Track routing accuracy: did the selected composition outperform alternatives on this problem profile?

---

## Evaluation and Trace Infrastructure

**Current state:** Langfuse captures token flows and run metadata.
**Required state:** Langfuse (or a layer above it) captures **structural decisions**, not just execution traces.

### What Every Run Must Log

```yaml
run_id: unique identifier
timestamp: ISO 8601
problem_profile: inferred ProblemProfile at intake
composition_selected: which primitive sequence was chosen
composition_alternatives: what other compositions were considered
routing_rationale: why this composition was selected
primitives_executed: ordered list with per-primitive cost, latency, token count
intermediate_outputs: output of each primitive step
final_output: delivered result
evaluation:
  automated_score: if available
  human_score: if collected
  criteria_used: what standards were applied
failure_signals:
  - type: [timeout, incoherence, constraint_violation, hallucination, user_rejection, cost_overrun]
  - primitive_where_failure_occurred: identifier
  - severity: [minor, major, critical]
transfer_flag: was this composition reused from a different problem class?
transfer_success: did it work in the new context?
```

### Implementation Tasks

- [ ] Extend Langfuse trace schema (or build a thin layer on top) to capture the fields above
- [ ] Build a `RunRecord` data model in FastAPI
- [ ] Create a `/runs/log` endpoint that agents call at composition selection time and at each primitive boundary
- [ ] Build a `/runs/evaluate` endpoint for post-hoc human and automated scoring
- [ ] Store RunRecords in a queryable format (Postgres or Pinecone metadata)

---

## Adaptive Routing

### Current State
Static dispatch: problem comes in, human or hardcoded logic selects a protocol.

### Target State
Learned routing: problem comes in, system infers ProblemProfile, queries historical RunRecords for similar profiles, selects the composition with best fitness on that profile region, executes, logs, and learns.

### Routing Loop

```
1. Intake: receive task, infer ProblemProfile
2. Retrieve: query RunRecord store for similar ProblemProfiles
3. Rank: score candidate compositions by historical fitness on similar profiles
4. Select: choose composition (with exploration/exploitation balance)
5. Execute: run the primitive sequence
6. Evaluate: score the output
7. Store: write RunRecord with full trace
8. Update: adjust routing weights for this ProblemProfile region
```

### Implementation Tasks

- [ ] Build `ProblemProfile` similarity function (cosine over encoded dimensions, or embedding-based)
- [ ] Build a routing index: ProblemProfile region -> ranked list of compositions with fitness scores
- [ ] Implement exploration rate: X% of runs try a non-top-ranked composition to avoid local optima
- [ ] Build a nightly or weekly batch job that recalculates routing weights from accumulated RunRecords
- [ ] Dashboard: visualize which compositions are winning on which profile regions, and where coverage is thin

---

## Composition Mutation and Evolution

Once routing is instrumented, the system can begin generating new compositions, not just selecting from existing ones.

### Mutation Operations

```
swap_primitive:     replace one primitive in a composition with another
reorder:            change primitive execution order
insert_primitive:   add a primitive step
remove_primitive:   drop a primitive step
branch:             add conditional logic (if score < threshold, escalate)
parallelize:        run two primitives concurrently instead of sequentially
merge:              combine two compositions that work on related subproblems
```

### Implementation Tasks

- [ ] Represent compositions as mutable data structures (DAGs of primitives)
- [ ] Build a mutation engine that applies random or heuristic mutations to existing compositions
- [ ] Run mutated compositions on held-out problem sets
- [ ] Compare mutated vs. parent composition on evaluation metrics
- [ ] Retain improvements, discard regressions
- [ ] Log lineage: every composition should track its parent composition and mutation history

### Falsification Test
If mutated compositions do not outperform parent compositions on transfer tasks within 90 days of instrumentation, the emergence thesis may be over-romanticized. Fallback: clean small library plus strong routing heuristics.

---

## Key Health Metrics

Track these as leading indicators of whether the system is compressing or just expanding.

| Metric | Compression Signal | Expansion Signal |
|---|---|---|
| Active protocol count | Plateaus or declines | Keeps climbing linearly |
| Task coverage | Growing | Flat or tied to protocol count |
| Avg coordination steps per run | Declining | Stable or rising |
| Cross-domain transfer rate | Rising | Near zero |
| Routing accuracy | Improving | Flat |
| Token/tool cost per equivalent output | Declining | Stable or rising |
| Failure prediction accuracy | Improving | Not measured |
| Composition reuse rate | Rising | Every problem gets a bespoke composition |

**The single most important leading indicator:** shrinking protocol library with rising capability coverage.

---

## Interface Strategy

### Principle: Push Interfaces Upward, Keep Control Downward

```
Layer 3 (Human):    Natural language intent + typed constraints + evaluation criteria
Layer 2 (System):   Composition selection, primitive orchestration, routing logic
Layer 1 (Runtime):  Tool calls, LLM invocations, retrieval, JSON/graph wiring
Layer 0 (Infra):    Langfuse traces, RunRecords, cost tracking, observability
```

The human operates at Layer 3. Everything below is compiled. Node graphs, JSON workflows, and tool wiring are Layer 1 artifacts, never the primary authoring surface.

### Implementation Tasks

- [ ] Build an intent capture interface: user describes task in natural language, system infers ProblemProfile and proposes a composition
- [ ] Allow constraint specification: cost ceiling, latency budget, required primitives, forbidden primitives, evaluation criteria
- [ ] Provide composition preview: before execution, show the user what primitive sequence will run and why
- [ ] Support override: user can modify the proposed composition before execution
- [ ] Post-execution: show trace, scores, and routing rationale in a human-readable format

---

## Implementation Phases

### Phase 1: Instrumentation (Weeks 1-4)
- Define primitive interface and candidate set
- Map existing protocols to primitive compositions
- Extend Langfuse traces to capture structural decisions
- Build RunRecord data model and logging endpoints
- Build ProblemProfile schema and classifier

### Phase 2: Routing (Weeks 5-8)
- Build ProblemProfile similarity function
- Build routing index from historical RunRecords
- Implement composition selection with exploration rate
- Build routing dashboard
- Begin collecting transfer metrics

### Phase 3: Mutation (Weeks 9-14)
- Implement composition mutation operations
- Build held-out evaluation pipeline
- Run first generation of mutated compositions
- Compare against parent compositions
- Assess falsification condition

### Phase 4: Interface (Weeks 12-16, overlapping)
- Build intent capture surface
- Build constraint specification
- Build composition preview and override
- Build post-execution trace viewer

---

## What This Spec Deletes

If this spec is correct, the following become unnecessary or demoted:

- Manual protocol authoring as a primary activity (becomes seeding, not building)
- Node-based workflow design as a user-facing interface (becomes a compiled layer)
- Protocol count as a progress metric (replaced by coverage, transfer, and compression metrics)
- Domain-specific protocol families as the unit of IP (replaced by learned routing + primitive grammar)

---

## Falsification Conditions

This spec is wrong if:

1. The primitive set cannot express 80%+ of existing protocols as compositions
2. Learned routing does not outperform static dispatch within 90 days of instrumentation
3. Mutated compositions do not outperform parents on transfer tasks
4. Protocol count continues rising linearly with task coverage
5. The system cannot predict failure modes better than random after 6 months of trace data

If conditions 1-3 fail, fallback to: small curated library + strong routing heuristics + manual composition. That is still a good business. It is just not the compression thesis.

---

## One Sentence

**Build a system that learns lower-description-length coordination schemas that generalize across more problem environments.**
