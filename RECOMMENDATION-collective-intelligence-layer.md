# Recommendation: ACI (Artificial Collective Intelligence) Layer

**Status:** Draft for CPO/CTO Review
**Date:** 2026-03-09
**Decision Owners:** CPO, CTO

---

## Executive Summary

CE-AGENTS is currently structured as a collection of independent protocol implementations (Walk, Debate, Review Board, AAR, etc.) across two product repositories (CE-Evals, coordination-lab). This recommendation proposes elevating **Artificial Collective Intelligence (ACI)** to a first-class architectural concept — a shared horizontal layer that sits above individual protocols and below evaluation/reporting.

> **Note:** We use the term "ACI" rather than "CI" to avoid confusion with CI/CD (Continuous Integration / Continuous Deployment).

The core reframe: CE-AGENTS is not a protocol library. It is a **collective cognition system with multiple protocol modes**.

This document presents the case, the architectural options, and the tradeoffs. It does not prescribe — it asks CPO and CTO to evaluate and decide.

---

## The Problem

Today each protocol is its own closed universe:
- Walk generates diverse perspectives
- Debate produces adversarial reasoning
- Review Board runs quality checks
- AAR captures lessons learned

But nothing connects them into a learning whole. There is no shared instrumentation, no cross-protocol memory, no system-level understanding of which agents, pairings, or protocols actually produce value.

Without an ACI layer, scaling to more protocols just means more parallel outputs — not more intelligent outputs.

## The Standard

A multiagent system is not collectively intelligent merely because many agents exist, outputs are merged, votes are taken, or a synthesizer writes a summary.

Collective intelligence emerges when the system measurably improves:
- Search breadth and depth
- Error correction
- Memory and calibration
- Coordination and adaptation
- Division of cognitive labor
- Quality of disagreement
- Learning from outcomes

**Proposed working definition for CE-AGENTS:**

> The system's ability to produce better interpretations, decisions, and adaptations through structured interaction among differentiated agents than those agents, or a monolithic model, would produce independently.

This is testable.

---

## What Changes

### 1. Protocol Classification by Collective Function

Rather than treating protocols as interchangeable answer-generators, classify them by what collective function they optimize.

| Function | Optimizes For | Example Protocols |
|----------|--------------|-------------------|
| **Exploration** | Diversity, reframing, hidden-variable discovery, orthogonal search | Walk, Wildcard Walk, divergent search |
| **Adjudication** | Critique, falsification, decision narrowing, conflict resolution | Debate, Review Board, Trade Study, Red Team |
| **Coordination** | Sequencing, decomposition, task interdependence, workload shaping | Planner/executor, hierarchical delegation, staff planning |
| **Learning** | Reflection, postmortem, memory updates, protocol improvement | AAR, debrief, evaluator loops, outcome review |

This is not a rigid taxonomy — protocols can contribute to multiple functions. But each should have a **primary** contribution clearly stated.

### 2. Protocol Spec Extension

Every protocol spec gains a new required section:

```
## ACI Contribution

- **Primary contribution:** [which dimension this protocol improves]
- **Secondary contribution:** [additional value]
- **Failure mode reduced:** [what class of collective failure this prevents]
- **Telemetry emitted:** [what signals feed back to the shared layer]
```

**Concrete examples:**

**Walk**
- Primary: Search diversity and representation change
- Secondary: Hidden-variable discovery
- Failure mode reduced: Fixation and premature convergence
- Telemetry: Lens novelty, salience quality, wildcard value, disagreement survival

**Review Board**
- Primary: Independent challenge and error correction
- Secondary: Risk surfacing
- Failure mode reduced: Builder bias, optimism, unchallenged synthesis
- Telemetry: Critique quality, risk hit rate, overturned claims

**AAR**
- Primary: Learning and adaptation
- Secondary: Calibration
- Failure mode reduced: Repeating ineffective coordination patterns
- Telemetry: Expected vs actual, protocol miss types, agent contribution hindsight

### 3. Shared Telemetry Framework

A system-level instrumentation layer that tracks across all protocols:

| Signal | What It Measures |
|--------|-----------------|
| Agent non-redundancy | Which agents contributed genuinely different value |
| Pairing strength | Which agent combinations produced strongest outputs |
| Protocol yield | Which protocols generated best downstream decisions |
| Disagreement productivity | Which disagreement patterns were productive vs noise |
| Over-selection detection | Which agents are picked often but contribute little |
| Lens underutilization | Which perspectives are underused but high-leverage |
| Synthesis integrity | Which synthesis patterns erase too much tension |
| Outcome survival | Which outputs survived real-world testing |

### 4. Evaluation Stack Extension

Current eval scores answer quality. The extension scores **collective performance**:

- **Diversity quality** — did agents bring genuinely different transforms?
- **Redundancy penalty** — how much output was duplicated effort?
- **Critique usefulness** — did challenges improve the result?
- **Synthesis integrity** — did the final output preserve productive tension?
- **Calibration** — does the system know what it doesn't know?
- **Transfer learning** — did prior runs improve this one?
- **Protocol efficiency** — useful insights per unit of compute/time

---

## Six Dimensions for Ongoing Assessment

Every protocol, regardless of family, should be evaluated on:

1. **Cognitive diversity** — Do agents bring genuinely different transforms, or just stylistic variation?
2. **Coordination quality** — Do agents build on one another productively, or talk past one another?
3. **Error correction** — Does the protocol expose and correct bad reasoning, blind spots, false confidence?
4. **Memory and accumulation** — Does the system preserve what it learned so future runs improve?
5. **Adaptive selection** — Does the system learn which agents, lenses, and interactions add value in which situations?
6. **Outcome coupling** — Do results from reality feed back into protocol behavior, scoring, and promotion?

---

## Architectural Options

### Option A: Lightweight — Spec and Eval Changes Only

**What:** Add the ACI section to protocol specs and extend the eval rubric. No new runtime infrastructure.

- Lowest effort, fastest to ship
- Forces design discipline immediately
- No runtime telemetry or cross-protocol learning
- Good starting point if you want to iterate

### Option B: Instrumented — Add Telemetry Layer

**What:** Option A plus a shared telemetry framework that collects signals from every protocol run.

- Enables data-driven protocol improvement
- Requires schema design and storage decisions
- Moderate engineering effort
- Enables the "which agents/protocols actually work" question

### Option C: Adaptive — Full Learning Loop

**What:** Option B plus feedback loops that use accumulated telemetry to adjust agent selection, protocol routing, and synthesis behavior over time.

- The full vision: a system that gets smarter
- Highest effort, longest runway
- Requires outcome coupling (real-world feedback)
- This is where the moat lives

### Recommended Path

Start with **Option A now**, instrument toward **Option B** as protocols are integrated into the monorepo, and design toward **Option C** as the north star. Each option is additive — nothing needs to be thrown away.

---

## The Strategic Claim

If CE-AGENTS does this well, the moat is not "we have N protocols."

The moat is:

> **We have an instrumented ACI engine that knows how to compose, critique, learn, and adapt across protocols.**

That shifts the competitive position from "protocol library" to "learning collective" — a fundamentally different product category.

---

## Decisions Requested

1. **Adopt the reframe?** — Should CE-AGENTS position itself as a collective cognition system rather than a protocol library?

2. **Which option to start with?** — A (spec discipline), B (instrumented), or C (full adaptive)?

3. **Protocol classification** — Should protocols be formally classified by collective function (Exploration, Adjudication, Coordination, Learning)?

4. **Spec requirements** — Should the ACI Contribution section become mandatory for all protocol specs?

5. **Eval extension** — Should collective performance metrics be added to CE-Evals alongside answer quality metrics?

6. **Scope** — Should ACI apply only to product protocols (CE-Evals, coordination-lab), or also to internal operational agents (ce-c-suite)?

---

## Appendix: Impact on Existing Repos

### Product repos (in scope)

| Repository | Impact |
|-----------|--------|
| **CE-Evals** | Eval rubrics extended with ACI performance dimensions; new scoring categories |
| **coordination-lab** | Protocol specs gain ACI section; protocols classified by collective function; telemetry schema defined |
| **ce-agents (monorepo)** | ACI layer becomes a shared module; telemetry storage and reporting live here |

### Operational repo (out of scope by default)

| Repository | Notes |
|-----------|-------|
| **ce-c-suite** | Internal company operations tool, not part of the product. Could optionally benefit from ACI instrumentation if CPO/CTO decide multiagent operational workflows should also participate in collective learning. Separate decision. |

### Monorepo status

The ce-agents monorepo is currently a skeleton (README + gitignore). The folder structure described in the README does not yet exist — sub-projects have not been integrated. This is the right moment to introduce ACI as a foundational layer before integration happens.

---

*This document is a recommendation for CPO/CTO decision. It presents options and tradeoffs, not prescriptions.*
