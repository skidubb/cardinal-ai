# Design: Self-Evolving Intelligence Platform

**Date:** 2026-03-10
**Status:** Approved
**Milestone:** Post-Full Stack Integration (next milestone)
**Approach:** Distributed Loops with Shared Telemetry Store

---

## Overview

Three independent loops — Learning, Routing Enhancement, and Platform Steward — share a common telemetry store and operate autonomously. A Self-Evolution Engine runs periodically to synthesize patterns across all three loops and propose new features with draft specs. The user greenlights all structural changes.

### Design Principles

- **No manual scoring burden** — ground truth comes from LLM-as-judge (CE-Evals) and protocol execution telemetry
- **Protocol function alignment** — learning respects what each protocol is for; exploration protocols are optimized for diversity, never consensus
- **Protocol selection automated, agent composition manual** — routing picks protocols/chains, the user picks agents
- **Recommend + spec, user greenlights** — the system proposes and specs changes, never implements autonomously
- **Append-only telemetry** — raw data is immutable; aggregates are computed views that can be re-derived
- **Independent shippability** — each loop can be deployed and deliver value independently

### Architecture

```
┌──────────────────────────────────────────────────────┐
│              Shared Telemetry Store                   │
│  Postgres (structured) + Pinecone (embeddings)       │
│  Langfuse (traces — existing, not duplicated)        │
└─────┬──────────────┬───────────────┬─────────────────┘
      │              │               │
 ┌────▼────┐   ┌─────▼─────┐   ┌────▼──────┐
 │ Learning │   │  Routing  │   │ Platform  │
 │  Loop    │   │  Engine   │   │ Steward   │
 └────┬─────┘   └─────┬─────┘  └─────┬─────┘
      │              │               │
      └──────────┬───┘───────────────┘
           ┌─────▼──────┐
           │ Self-Evol.  │
           │   Engine    │
           └─────┬──────┘
                 ▼
         proposals/ queue
          (user reviews)
```

---

## 1. Shared Telemetry Store

### Purpose

Foundation layer that all loops read from. Extends existing Langfuse tracing and Postgres persistence — does not replace them.

### Signal Categories

| Signal Category | Examples | Source |
|---|---|---|
| Execution profile | Wall time, token spend, agent turn count, rounds completed | Protocol runtime (partially exists) |
| Contribution analysis | Per-agent token ratio, unique-point count, agreement/dissent pattern | Post-run analysis of protocol output |
| Eval scores | CE-Evals LLM-as-judge scores, per-dimension | Automated eval pass after each run |
| Protocol function alignment | How well the run served its primary ACI function | Eval rubric keyed to protocol classification |
| Routing context | Question embedding, classification, protocol selected and why | Routing engine at invocation time |

### Storage

- **Postgres** — structured telemetry in new tables alongside existing `protocol_runs` in `ce-db`
- **Langfuse** — continues as trace/span viewer, not duplicated
- **Pinecone** — question embeddings + outcome pairs for routing similarity search (only new infra dependency)

### Schema (conceptual)

```
run_telemetry
  - run_id (FK to protocol_runs)
  - protocol_key
  - protocol_function (exploration | adjudication | coordination | learning)
  - wall_time_ms
  - total_tokens
  - total_cost
  - eval_scores (JSONB — keyed by dimension)
  - question_embedding_id (FK to Pinecone record)
  - created_at

agent_contributions
  - run_id (FK)
  - agent_key
  - token_count
  - unique_points_raised
  - dissent_count
  - contribution_score (computed)

protocol_performance
  - protocol_key
  - question_type
  - rolling_avg_score
  - run_count
  - last_updated
  (materialized view, refreshed per-run or on schedule)

improvement_proposals
  - id
  - type (prompt_refinement | chain_recommendation | pattern_observation | feature_proposal)
  - protocol_key (nullable — may be cross-cutting)
  - title
  - trigger_description
  - evidence (JSONB)
  - recommendation (text)
  - draft_spec (text, nullable)
  - expected_impact
  - scope (S | M | L)
  - status (pending | approved | rejected | implemented)
  - outcome_score (nullable — filled after implementation + measurement)
  - created_at
  - reviewed_at

proposal_outcomes
  - proposal_id (FK)
  - pre_change_scores (JSONB)
  - post_change_scores (JSONB)
  - delta
  - measurement_period_days
  - conclusion (improved | neutral | regressed)
```

### Design Principle

Raw data is append-only and immutable. Aggregates and derived insights are computed views. If analysis logic improves, conclusions can be re-derived from raw data.

---

## 2. Learning Loop

### Purpose

The core intelligence engine. Detects what's working, what's degrading, and proposes improvements — always aligned to each protocol's ACI function.

### Two Cadences

**Real-time (per-run):**
1. Run CE-Evals against the output — scored on dimensions mapped to the protocol's ACI function
2. Extract contribution metrics per agent from the run transcript
3. Write telemetry to the store
4. Compare scores against the protocol's rolling baseline — flag significant deviations

**Batch (scheduled — daily or after N runs):**
1. Analyze trends across recent runs — improving, degrading, or flat
2. Identify cross-run patterns (e.g., "TRIZ after Cynefin scores 30% higher on novelty")
3. Generate improvement proposals to the queue

### Function-Aligned Learning

| Protocol Function | What "better" means | Learning targets |
|---|---|---|
| **Exploration** (Walk, Wildcard, divergent) | Higher diversity, more novel frames, less redundancy | Prompt phrasing for different perspectives, lens selection |
| **Adjudication** (Debate, Red Team, Review Board) | Stronger challenges, more errors caught, productive disagreement | Critique prompt sharpness, round count, dissent preservation |
| **Coordination** (Planner, delegation, staff) | Better decomposition, fewer gaps, cleaner handoffs | Sequencing templates, decomposition granularity |
| **Learning** (AAR, debrief, outcome review) | More actionable takeaways, better calibration | Reflection prompt depth, recommendation specificity |

A Walk protocol will never be optimized for "reaching consensus faster" — that would violate its nature.

### Proposal Types

**Prompt refinements** — current prompt, proposed rewrite, eval evidence, target dimension. Example: "P06 TRIZ divergent prompt scores 0.4 on novelty. Proposed rewrite scores 0.7 in A/B eval."

**Chain recommendations** — data-backed suggestions for protocol sequencing. Example: "Cynefin → TRIZ scores 35% higher on actionability than standalone TRIZ (n=12)."

**Pattern observations** — insights for user judgment, not code changes. Example: "3-round debates outperform 2-round on error correction, diminishing returns at 4+."

### Agent Self-Improvement

Per-agent contribution scores tracked across many runs and protocols. When a pattern emerges (e.g., "CFO scores low on creative reframing, high on risk identification"), the loop proposes system prompt adjustments. Same proposal queue — user decides.

### Boundaries

- Does not modify any prompt, config, or protocol code autonomously
- Does not change agent system prompts without approval
- Does not retrain or fine-tune models
- Does not discard low-scoring protocols — surfaces for review

---

## 3. Routing Engine Enhancement

### Purpose

Upgrade the existing routing logic with performance-weighted protocol selection. Not a rebuild — an augmentation.

### Current → Enhanced

| Capability | Current | Enhanced |
|---|---|---|
| Protocol selection | Rule-based / manual | Rule-based + performance-weighted scoring |
| Chain construction | Hardcoded chains | Chains validated and ranked by historical outcome data |
| Question classification | Existing classifier | Same classifier + embedding similarity against past runs |
| Confidence signal | None | Confidence level based on historical match depth |

### How Telemetry Feeds Routing

The router gains access to a materialized view: **protocol performance by question type**.

```
"pricing uncertainty" questions:
  - Cynefin → TRIZ → Popper: avg score 0.82 (n=12)
  - TRIZ standalone:          avg score 0.61 (n=8)
  - Debate (3-round):         avg score 0.73 (n=5)
```

Flow: classify question (existing) → look up historical performance → rank protocol chains → return recommendation with confidence.

### Pinecone Integration

Question embeddings stored alongside run outcomes. When classification is ambiguous, semantic similarity fallback: "Find the 10 most similar past questions, what protocols scored highest?" Handles edge cases the rule-based classifier hasn't seen.

### What Stays the Same

- User still picks agents — routing selects protocols/chains only
- Existing routing rules remain as baseline — performance data augments, doesn't replace
- User can always override

---

## 4. Platform Steward

### Purpose

Autonomous maintenance agents that keep the platform healthy without user intervention on routine tasks.

### Health Monitor

**Cadence:** Daily + on-commit CI hook

- Import checks across all projects — catches broken cross-project references
- Dependency version drift detection
- Config validation — `ce-shared env_check` + Langfuse, Postgres, Pinecone reachability
- Test suite execution — `pytest -m "not integration"` across all projects
- **Action:** Files issues to maintenance queue. Fixes trivially deterministic problems (stale lockfiles, import reordering) with a commit. Alerts user for anything requiring judgment.

### Eval Regression Detector

**Cadence:** After every batch learning cycle

- Compares current protocol scores against 30-day rolling averages
- Correlates score drops with specific changes (model updates, prompt changes, dependency bumps)
- **Action:** Generates regression report with correlation analysis and revert recommendation. Goes to proposal queue.

### Documentation Sync

**Cadence:** Weekly + on significant code changes

- Diffs protocol implementations against their specs
- Checks agent registry against actual agent definitions
- Validates CLAUDE.md accuracy against codebase state
- **Action:** Sync report with specific suggested edits. Does NOT auto-edit documentation.

---

## 5. Self-Evolution Engine

### Purpose

Synthesizes patterns across all three loops and proposes new capabilities with draft specs.

### Three Inputs

1. **Learning loop patterns** — recurring proposal themes suggesting structural gaps ("I keep proposing prompt tweaks for the same weakness — needs a protocol-level fix")
2. **Steward observations** — maintenance patterns suggesting missing infrastructure ("Same import break every time a new protocol is added — need a registration hook")
3. **Routing gaps** — question types with no high-scoring protocol or consistently low router confidence

### Output Format

Feature Proposal Documents written to `proposals/`:

```
proposals/
  2026-04-15-exploration-protocol-gap-org-design.md
  2026-04-22-auto-chain-validation-hook.md
  2026-05-01-agent-cfo-prompt-restructure.md
```

Each follows:

```markdown
## Proposal: [Title]
**Type:** new-protocol | protocol-enhancement | agent-improvement |
         infrastructure | maintenance-automation
**Trigger:** [What data pattern prompted this]
**Evidence:** [Specific telemetry — scores, trends, frequencies]
**Recommendation:** [What to build/change]
**Expected impact:** [Which scores/metrics improve, by how much]
**Scope estimate:** [S/M/L complexity — not time estimates]
**Risk if ignored:** [What continues to degrade or stay unoptimized]

## Draft Spec
[Architecture sketch, key components, data flow,
 integration points — enough to start an implementation session]
```

### Cadence

- **Weekly synthesis** — reviews past week's telemetry, proposals, steward reports. Produces 0-3 proposals (evidence-driven, not quota-driven).
- **Quarterly retrospective** — deep analysis across full history. Systemic patterns, architectural debt, strategic opportunities. Produces a "Platform Health & Evolution Report."

### Closed Loop

```
Evidence accumulates in telemetry store
  → Evolution engine detects pattern
    → Writes proposal with draft spec
      → User reviews (approve / reject / modify)
        → Approved proposals become implementation tasks
          → After implementation, learning loop tracks score changes
            → Outcome feeds the next evolution cycle
```

The system learns which kinds of proposals actually deliver value.

### Boundaries

- Does not implement anything — recommend + spec only
- Does not prioritize across proposals — user's consulting judgment
- Does not propose changes to its own evolution logic (no recursive self-modification of the meta-layer)

---

## Implementation Sequencing

This milestone comes after Full Stack Integration is complete. Suggested phase ordering:

| Phase | Component | Why this order |
|---|---|---|
| 1 | Telemetry Store schema + collection | Foundation — nothing learns without data |
| 2 | Platform Steward | Immediate maintenance value, lowest complexity |
| 3 | Learning Loop (per-run) | Start accumulating eval scores and contribution data |
| 4 | Routing Enhancement | Needs accumulated data from Phase 3 to be useful |
| 5 | Learning Loop (batch) | Pattern detection across accumulated runs |
| 6 | Self-Evolution Engine | Needs all three loops producing data to synthesize |

Each phase is independently deployable and delivers value on its own.

## Dependencies

- **CE-Evals** — must support automated eval runs triggered by protocol completion (may need a thin API or callable interface)
- **Pinecone** — question embedding storage for routing similarity (already in the stack)
- **ACI protocol classification** — protocols must be tagged by function (exploration/adjudication/coordination/learning) before function-aligned learning works
- **Full Stack Integration milestone** — API, UI, and deployment must be complete so telemetry captures real client usage, not just CLI test runs

## New Infrastructure

| Component | What | Notes |
|---|---|---|
| Pinecone index | Question embeddings + outcome pairs | Only new external dependency |
| Postgres tables | Telemetry schema (5 tables) | Extends existing ce-db |
| Scheduled jobs | Batch learning, steward checks, evolution synthesis | Cron or task queue (Celery, APScheduler, or similar) |
| Proposals directory | Feature proposals with draft specs | File-based, git-tracked |

---

*Design approved 2026-03-10. Implementation planning deferred to post-Full Stack Integration milestone.*
