# The Coordination Lab

## A Comprehensive Multi-Agent Research Program for Cardinal Element

**Scott Ewalt | Cardinal Element | February 2026**

---

## Program Overview

This document defines a systematic research program to test every major coordination architecture against every major problem type, with tool-access conditions as a controlled variable. The program builds on the v1/v2 evaluation studies (February 2026) and extends them from 5 modes × 10 questions to a full matrix of coordination protocols × problem types × tool conditions.

The goal: build an empirically-grounded **adaptive router** for C-Suite that selects the optimal coordination architecture, tool-access level, and evaluation rubric for any incoming strategic question — automatically.

---

## Part 1: Problem Type Taxonomy

Eight problem types, derived from the v1/v2 evaluation data plus five coordination traditions (game theory, intelligence analysis, organizational theory, systems thinking, design thinking).

### 1.1 The Eight Types

| # | Problem Type | Core Challenge | Example Question | v1/v2 Coverage |
| --- | --- | --- | --- | --- |
| 1 | **Integration** | Combine multiple valid perspectives into coherent plan | "Hire consultant or invest in AI automation?" | Strong (synthesis won these) |
| 2 | **Adversarial** | Stress-test assumptions under competitive pressure | "Competitor raised $20M. How do we respond?" | Strong (debate won these) |
| 3 | **Stakeholder Tension** | Satisfy competing parties with hard constraints | "Largest client demands 25% discount" | Moderate (negotiate won these) |
| 4 | **Diagnostic** | Identify root cause of underperformance | "Revenue per client dropped 22% over two quarters. Why?" | Not tested |
| 5 | **Exploration** | Generate novel options in open-ended space | "$200K free cash flow, no urgent needs. What should we do?" | Not tested |
| 6 | **Prioritization** | Rank competing valid options defensibly | "8 growth initiatives, 18 months runway. Rank them." | Not tested |
| 7 | **Paradox/Wicked** | Sharpen irresolvable tensions for management | "Scale without hiring when value prop is human expertise" | Not tested |
| 8 | **Risk/Pre-Mortem** | Identify failure modes in an accepted plan | "We took the $500K enterprise deal. What kills us?" | Not tested |

### Supplemental Types (Lower Priority, Phase 3+)

| # | Problem Type | Core Challenge | Example |
| --- | --- | --- | --- |
| 9 | **Sequential/Dependency** | Determine optimal ordering under constraints | "Launch PLG, hire consultant, rebrand — in what order on $150K?" |
| 10 | **Empathy/Stakeholder Modeling** | Model what the other party actually wants | "Client VP of Engineering pushing back on SOW. How do we approach renewal?" |
| 11 | **Estimation/Forecasting** | Calibrate quantitative predictions | "What probability does the enterprise deal close? What Q3 revenue?" |
| 12 | **Systemic/Structural** | Map how the system actually works before intervening | "Delivery overruns: capacity loop, scope loop, or communication loop?" |

### 1.2 Benchmark Questions Per Type

Each problem type requires 4 benchmark questions minimum (target: 5) to achieve sufficient signal. Questions must meet the same design criteria as v2: specific dollar amounts/percentages/timelines, genuine tension between 2-3+ functions, no obvious right answer.

**Phase 1 Questions (Types 1-8, 32 questions total):**

### Type 1: Integration (retain v2 questions + add 1 new)

- Q1.1: PLG tier alongside consulting (from v2)
- Q1.2: Capacity — hire vs. AI automation (from v2)
- Q1.3: Delivery overrun — 3 of 5 engagements late (from v2)
- Q1.4: Margin vs. speed — $12 API cost on $2,500 deliverable (from v2)
- Q1.5 [NEW]: "We can either build a proprietary data pipeline for client reporting ($40K, 3 months) or use a white-labeled SaaS tool ($800/mo, live in 2 weeks). We have 6 active clients expecting dashboards by Q2."

### Type 2: Adversarial (retain v2 competitive + add 3 new)

- Q2.1: Competitor raised $20M, offering free audits (from v2)
- Q2.2 [NEW]: "A former client's Head of Growth is now publicly advocating for bringing all AI consulting in-house. She has 12K LinkedIn followers in our ICP. Two prospects have cited her posts in discovery calls this week."
- Q2.3 [NEW]: "McKinsey just published a free 40-page AI transformation playbook that covers 60% of what we deliver in our $25K audit. Three prospects have sent it to us asking 'how is yours different?'"
- Q2.4 [NEW]: "Our top-performing subcontractor just launched their own competing practice. They have deep relationships with 3 of our 8 active clients and know our methodology intimately."

### Type 3: Stakeholder Tension (retain v2 questions + add 1 new)

- Q3.1: Pricing — free discovery call vs. premium positioning (from v2)
- Q3.2: Client concentration — 40% revenue client demands 25% discount (from v2)
- Q3.3: Conference spend — $50K on $80K budget (from v2)
- Q3.4: Enterprise opportunity — $500K outside ICP (from v2)
- Q3.5 [NEW]: "A strategic partner wants to co-sell our audit as part of their platform bundle at 40% margin to us (vs. our normal 70%). They guarantee 20 leads/quarter. Our current pipeline generates 8 qualified leads/quarter organically."

### Type 4: Diagnostic (all new)

- Q4.1: "Revenue per client dropped 22% over the last two quarters despite adding 3 new clients. Client count is up 37%, total revenue is up 6%. NPS hasn't changed. What's happening?"
- Q4.2: "Our sales cycle lengthened from 18 days to 41 days over the past 6 months. Win rate is stable at 35%. We haven't changed pricing, ICP, or outreach volume. Diagnose the cause."
- Q4.3: "Client satisfaction scores are 4.7/5.0 but renewal rate dropped from 80% to 55% this year. Exit interviews cite 'budget constraints' but our pricing hasn't increased. What's actually going on?"
- Q4.4: "Our AI automation tools reduced delivery time by 40% but profit margin per engagement decreased from 68% to 52%. We're doing more work faster but making less money. Why?"

### Type 5: Exploration (all new)

- Q5.1: "$200K in free cash flow, no urgent operational needs, 14 months runway at current burn. What should we do with it?"
- Q5.2: "We have 400 hours of recorded client discovery calls, 50 completed audit reports, and 3 years of engagement data. What could we build with these assets that we haven't considered?"
- Q5.3: "A university AI program wants to partner with us. They have 200 graduate students, access to compute resources, and want real-world projects. No specific terms proposed. What are the possibilities?"
- Q5.4: "We just discovered that our proprietary audit methodology produces a byproduct — a detailed competitive intelligence map for each client's market. We've been discarding this. What could it become?"

### Type 6: Prioritization (all new)

- Q6.1: "Rank these initiatives for a bootstrapped AI consultancy with $150K budget and 18 months runway: (a) hire senior consultant $120K, (b) build self-serve PLG tool $40K, (c) launch podcast/content series $15K, (d) attend 4 industry conferences $50K, (e) develop proprietary training curriculum $25K, (f) build partner channel program $10K, (g) invest in AI automation tools $35K, (h) open second geographic market $20K."
- Q6.2: "We have capacity for exactly 2 new client engagements this quarter. Rank: (a) $80K Fortune 500, 6-month timeline, low margin but logo value; (b) $35K Series B startup, 6-week sprint, high margin, potential for recurring; (c) $120K government contract, 9-month timeline, requires security clearance investment; (d) $50K mid-market SaaS, 8-week engagement, strong referral network in ICP."
- Q6.3: "Prioritize these product improvements for C-Suite: (a) add 4 new agent roles, (b) build web UI, (c) add write-access integrations (Salesforce/HubSpot), (d) implement cross-model support (GPT/Gemini), (e) build client-facing dashboard, (f) improve debate protocol to 3 rounds."
- Q6.4: "We have one senior consultant available for 60 hours this month. Allocate across: (a) close $80K prospect in final negotiation, (b) rescue at-risk $45K engagement running 3 weeks late, (c) develop new AI audit methodology for healthcare vertical, (d) create sales enablement content for Q2 pipeline, (e) train 2 junior contractors on delivery methodology."

### Type 7: Paradox/Wicked (all new)

- Q7.1: "How do we scale without hiring when our value proposition is human expertise applied through AI? Every scaling mechanism (PLG, automation, templates) dilutes the 'bespoke' positioning that commands premium pricing."
- Q7.2: "Our best growth strategy requires us to give away our core methodology (open-source audit framework) to build authority, but our revenue model depends on that methodology being proprietary and scarce."
- Q7.3: "We need to be specialists (AI consulting for subscription businesses) to win deals, but we need to be generalists (AI consulting for any business) to fill pipeline. Every positioning decision that improves close rate reduces pipeline volume and vice versa."
- Q7.4: "Our AI agents produce better strategic recommendations than most human consultants, but revealing this to clients undermines their willingness to pay human consulting rates. We're selling human expertise while delivering machine intelligence."

### Type 8: Risk/Pre-Mortem (all new)

- Q8.1: "We've decided to take the $500K enterprise engagement outside our ICP (2,000-person company vs. our usual 50-200). We've signed the SOW. What kills us?"
- Q8.2: "We're launching the self-serve PLG tier at $497/month alongside our $25K audit engagements. The board approved it last week. Pre-mortem this decision."
- Q8.3: "We've committed to presenting at 3 major conferences in Q2 ($40K total spend) and publishing weekly content. Our team is 2 people. Pre-mortem the content/conference strategy."
- Q8.4: "We've agreed to a 40% revenue-share co-sell arrangement with a larger platform partner who guarantees 20 leads/quarter. The contract is signed. What goes wrong?"

---

## Part 2: Coordination Protocol Inventory

### 2.1 Existing Protocols (from v1/v2)

| ID | Protocol | Source Tradition | Architecture |
| --- | --- | --- | --- |
| P1 | **Single Agent** | Baseline | 1 agent, no coordination |
| P2 | **Single+Context** | Baseline | 1 agent, all-role system prompt |
| P3 | **Parallel Synthesis** | — | N agents parallel → synthesis pass |
| P4 | **Multi-Round Debate** | Argumentation theory | N agents, 2 rounds rebuttals → synthesis |
| P5 | **Constraint Negotiation** | — | Debate + Haiku constraint extraction + propagation |

### 2.2 New Protocols to Implement

### From Liberating Structures (Emergence-Producing)

| ID | Protocol | LS Source | Architecture | Target Problem Type |
| --- | --- | --- | --- | --- |
| P6 | **TRIZ Inversion** | TRIZ | All agents attack same plan ("guarantee failure") → severity ranking | Risk/Pre-Mortem |
| P7 | **Wicked Questions** | Wicked Questions | Agents sharpen paradox from functional perspectives → facilitator finds deepest formulation | Paradox/Wicked |
| P8 | **Min Specs** | Min Specs | Agents propose minimum necessary constraints → facilitator identifies only truly essential ones via elimination rounds | Integration, Prioritization |
| P9 | **Troika Consulting** | Troika Consulting | 1 agent presents problem, 2 consult, presenter receives without rebutting → silent observer synthesizes | Empathy/Stakeholder |
| P10 | **Heard-Seen-Respected** | HSR | Agent A produces analysis → Agent B restates in own functional language → Agent A responds to restatement | Diagnostic, Exploration |
| P11 | **Discovery & Action Dialogue** | DAD | Agents identify positive deviance — "who's already solving this?" → surface uncommon practices | Diagnostic |
| P12 | **25/10 Crowd Sourcing** | 25/10 | Rapid generation → iterative cross-scoring → consensus with dissent noted | Prioritization |
| P13 | **Ecocycle Planning** | Ecocycle | Agents map initiatives to birth/maturity/destruction/renewal quadrants → disagreement = insight | Sequential, Prioritization |
| P14 | **1-2-4-All Progressive Aggregation** | 1-2-4-All | Solo → pairs → quads → all, each stage builds on prior (agents see previous stage output) | Exploration |
| P15 | **What/So What/Now What** | W³ | Round 1: what happened? Round 2: why does it matter? Round 3: what should we do? Separate agents per round | Diagnostic, Integration |

### From Intelligence Analysis

| ID | Protocol | Source | Architecture | Target Problem Type |
| --- | --- | --- | --- | --- |
| P16 | **Analysis of Competing Hypotheses (ACH)** | CIA/Heuer | Each agent champions a hypothesis → facilitator builds consistency matrix → disconfirmation-based elimination | Diagnostic |
| P17 | **Red Team / Blue Team / White Team** | Military/Intel | Red attacks plan, Blue defends, White judges which attacks succeeded (3-team, not 3-agent) | Risk/Pre-Mortem, Adversarial |
| P18 | **Delphi Method** | RAND Corporation | Iterative anonymous estimation → see distribution → revise → converge or identify genuine uncertainty | Estimation/Forecasting |

### From Game Theory / Mechanism Design

| ID | Protocol | Source | Architecture | Target Problem Type |
| --- | --- | --- | --- | --- |
| P19 | **Vickrey Auction** | Mechanism Design | Agents bid on resource allocation, second-price mechanism, truthful preference revelation | Prioritization, Resource Allocation |
| P20 | **Borda Count Voting** | Social Choice Theory | Agents submit ranked preferences → aggregation rule determines winner → dissent analysis | Prioritization |
| P21 | **Interests-Based Negotiation** | Fisher/Ury | Agents articulate interests (not just positions), explore trades across dimensions, BATNA-aware | Stakeholder Tension |

### From Organizational Theory

| ID | Protocol | Source | Architecture | Target Problem Type |
| --- | --- | --- | --- | --- |
| P22 | **Sequential Pipeline** | Thompson | CFO output → CTO input → CMO input, each agent reasons from upstream agent's actual conclusion | Sequential/Dependency, Integration |
| P23 | **Cynefin Probe-Sense-Respond** | Snowden | Agents propose small probes → simulate outcomes → adapt based on results → iterate | Paradox/Wicked, Exploration |

### From Systems Thinking

| ID | Protocol | Source | Architecture | Target Problem Type |
| --- | --- | --- | --- | --- |
| P24 | **Causal Loop Mapping** | System Dynamics | Agents map causal structure from own perspective → synthesis identifies agreed/disputed loops | Diagnostic, Systemic |
| P25 | **System Archetype Detection** | Senge | Specialized agent identifies known dysfunctional patterns (shifting burden, fixes that fail, eroding goals) | Diagnostic, Systemic |

### From Design Thinking

| ID | Protocol | Source | Architecture | Target Problem Type |
| --- | --- | --- | --- | --- |
| P26 | **Crazy Eights** | IDEO | Agents generate under extreme token constraint (100 tokens × 8 ideas) → enrichment pass develops best ones | Exploration |
| P27 | **Affinity Mapping** | IDEO | Agents generate observations → clustering agent groups by emergent similarity (not predefined roles) | Exploration, Diagnostic |

---

## Part 3: Tool-Access Decision Matrix

### 3.1 Tool-Access Levels

Three levels, not binary:

| Level | Description | Tools Available |
| --- | --- | --- |
| **T0: None** | Pure reasoning from training data + system prompt | None |
| **T1: Read-Only Retrieval** | Information lookup, no computation | Web search, SEC EDGAR, CRM read, document fetch |
| **T2: Full** | Retrieval + computation + write access | All T1 + financial calculators, pricing models, write APIs |

### 3.2 Tool-Access by Problem Type

Based on v1/v2 empirical data + theoretical framework:

| Problem Type | Recommended Tool Level | Rationale | Phase-Gating Notes |
| --- | --- | --- | --- |
| Integration | **T0** | v2 showed synthesis won without tools; tools risk conflicting data anchors across parallel agents | N/A |
| Adversarial | **T1** | v1 showed debate improved with data-grounded rebuttals; computation tools caused more errors than value | Enable for rebuttals only, not opening positions |
| Stakeholder Tension | **T1** | Constraint-based reasoning benefits from verifiable facts; but calculation tools confused agents in v1 | Enable for constraint verification phase only |
| Diagnostic | **T2** | Root cause analysis requires real data; confabulation risk highest without tools | Enable throughout |
| Exploration | **T0** | Tools narrow possibility space; web search produces conventional output | Exception: T1 in evaluation phase after generation |
| Prioritization | **T0 → T1** | Generate rankings tool-free; enable tools for cross-evaluation scoring phase | Phase-gated: T0 for generation, T1 for scoring |
| Paradox/Wicked | **T0** | Tools encourage premature resolution; the point is to sit with tension | Strictly no tools |
| Risk/Pre-Mortem | **T1** | Prevents imaginary risks; grounds failure modes in real business data | Enable throughout; computation tools optional |
| Sequential | **T1** | Downstream agents benefit from verified upstream data | Enable for verification, not generation |
| Empathy/Stakeholder | **T0 → T1** | Setup phase: tools for research on counterparty; execution: no tools (breaks simulation) | Phase-gated |
| Estimation | **T1** | Calibration benefits from base-rate data | Enable for evidence gathering, not for estimate generation |
| Systemic | **T1** | Causal models need grounding in real data flows | Enable for data verification |

### 3.3 Tool-Access by Protocol

| Protocol | Recommended Tool Level | Notes |
| --- | --- | --- |
| P1-P2 (Single/Context) | Match problem type | Baseline should match experimental condition |
| P3 (Synthesis) | Match problem type | Per-agent tool access identical |
| P4 (Debate) | T1 for rebuttals only | v1 data: tools helped rebuttals, not opening positions |
| P5 (Negotiate) | T1 for constraint verification | Constraints benefit from factual grounding |
| P6 (TRIZ) | T1 | Failure modes should be grounded |
| P7 (Wicked Questions) | T0 strictly | Premature resolution risk |
| P8 (Min Specs) | T0 | Constraint generation should come from reasoning |
| P16 (ACH) | T2 | Hypothesis testing requires data |
| P17 (Red/Blue/White) | T1 for Red, T0 for Blue, T0 for White | Red Team needs data to find real vulnerabilities; Blue defends from position; White judges impartially |
| P18 (Delphi) | T1 between rounds | Agents revise estimates based on evidence, not just peer estimates |
| P19-P20 (Auction/Voting) | T0 | Preference revelation should be uncontaminated |
| P22 (Sequential Pipeline) | T1 per stage | Each agent can verify upstream claims |
| P26 (Crazy Eights) | T0 strictly | Constraint = no external information |
| P27 (Affinity Mapping) | T0 for generation, T1 for clustering | Clusters should be emergent, not data-driven |

---

## Part 4: Evaluation Dimensions

### 4.1 Universal Dimensions (Score All Problem Types)

These 4 dimensions apply to every protocol × problem type combination:

| Dimension | Measures | Score Range |
| --- | --- | --- |
| **Specificity** | Concrete enough to act on? Named owners, timelines, dollar amounts? | 1-5 |
| **Internal Consistency** | Do recommendations align with each other? No contradictions? | 1-5 |
| **Reasoning Depth** | Claims backed by evidence/logic, not assertions? | 1-5 |
| **Completeness** | All relevant perspectives addressed? | 1-5 |

### 4.2 Problem-Type-Specific Dimensions

Each problem type adds 3 specialized dimensions to the 4 universal ones, for 7 total per evaluation (matching v1/v2 rubric structure):

### Integration Problems

| Dimension | Measures |
| --- | --- |
| Tension Surfacing | Genuine trade-offs identified, not just listed? |
| Actionability | Clear first step, owner, timeline, decision gates? |
| Constraint Awareness | Real-world limits acknowledged and incorporated? |

### Adversarial Problems

| Dimension | Measures |
| --- | --- |
| Threat Assessment Accuracy | Realistic evaluation of competitive threat severity? |
| Counter-Strategy Robustness | Response survives adversary's likely counter-moves? |
| Assumption Stress-Testing | Key assumptions explicitly challenged and defended? |

### Stakeholder Tension Problems

| Dimension | Measures |
| --- | --- |
| Interest Identification | Underlying interests (not just positions) surfaced? |
| Trade-off Transparency | What's being sacrificed is explicit, not hidden? |
| Constraint Satisfaction | Hard constraints respected; soft constraints optimized? |

### Diagnostic Problems

| Dimension | Measures |
| --- | --- |
| Hypothesis Coverage | All plausible root causes considered? |
| Disconfirmation Rigor | Evidence used to eliminate hypotheses, not just confirm? |
| Root Cause Specificity | Final diagnosis is specific and testable, not vague? |

### Exploration Problems

| Dimension | Measures |
| --- | --- |
| Novelty | Ideas that wouldn't emerge from obvious first-pass thinking? |
| Range/Diversity | Options span genuinely different strategic directions? |
| Development Depth | Best ideas developed beyond one-liner to actionable concept? |

### Prioritization Problems

| Dimension | Measures |
| --- | --- |
| Criteria Transparency | Ranking criteria explicit and defensible? |
| Sensitivity Analysis | Would rankings change under different assumptions? |
| Dissent Preservation | Minority rankings noted with rationale, not suppressed? |

### Paradox/Wicked Problems

| Dimension | Measures |
| --- | --- |
| Paradox Clarity | Tension articulated in its sharpest, most irresolvable form? |
| Premature Resolution Avoidance | Recommendations manage the tension rather than pretend to solve it? |
| Boundary Condition Mapping | Under what conditions does each side of the paradox dominate? |

### Risk/Pre-Mortem Problems

| Dimension | Measures |
| --- | --- |
| Failure Mode Coverage | Range of failure types identified (operational, financial, reputational, market)? |
| Severity Calibration | Risks appropriately classified by likelihood × impact? |
| Mitigation Specificity | Risk responses are concrete actions, not generic "monitor and adjust"? |

---

## Part 5: Implementation Phases

### Phase 1: Foundation (Weeks 1-4)

**Goal:** Implement 6 new protocols, write 32 benchmark questions, establish evaluation infrastructure.

### Week 1-2: Protocol Implementation

Build these 6 protocols first — they cover the highest-value problem types with the most tractable architectures:

| Priority | Protocol | Why First |
| --- | --- | --- |
| 1 | **P6: TRIZ Inversion** | Simplest new architecture (all agents same role: attacker). Tests Risk/Pre-Mortem type. |
| 2 | **P16: ACH** | Highest diagnostic value. Requires consistency matrix — new artifact type. |
| 3 | **P7: Wicked Questions** | Simplest LS translation. Tests whether LLMs can sharpen vs. resolve. |
| 4 | **P12: 25/10 Crowd Sourcing** | Tests prioritization. Requires cross-scoring mechanism — reusable for later protocols. |
| 5 | **P14: 1-2-4-All** | Tests exploration. Requires staged visibility — new orchestration pattern. |
| 6 | **P22: Sequential Pipeline** | Tests dependency reasoning. New orchestration pattern (output chaining). |

**Implementation pattern for each protocol:**

1. Define the orchestration flow (which agents, what order, what visibility)
2. Write system prompts for each agent role within the protocol
3. Define the output artifact structure (what gets persisted)
4. Implement the coordination loop in the Orchestrator
5. Test on 1 question manually before benchmark

### Week 2-3: Benchmark Question Finalization

- Draft all 32 Phase 1 questions (8 types × 4 each)
- Review each against design criteria: specific numbers, genuine tension, no obvious answer
- Pilot 1 question per type through Mode C (synthesis) as a sanity check
- Revise questions that produce flat/obvious responses

### Week 3-4: Evaluation Infrastructure

- Extend the blind judge protocol to support problem-type-specific dimensions
- Build the dimension selector: given a problem type, inject the correct 3 specialized dimensions
- Implement phase-gated tool access (per-round `tools_enabled` control)
- Extend output persistence to capture structural traces per protocol (constraint counts, hypothesis matrices, vote tallies, etc.)
- Build cost tracking fix (in-memory accumulator subclass from v2 Appendix C)

**Phase 1 Deliverable:** 6 new protocols + 5 existing = 11 protocols ready to test. 32 benchmark questions finalized. Evaluation infrastructure supports problem-type-specific rubrics and phase-gated tools.

---

### Phase 2: Core Evaluation (Weeks 5-8)

**Goal:** Run the primary test matrix and analyze results.

### The Phase 2 Test Matrix

Not every protocol runs against every problem type. Each protocol is tested against its target problem type(s) plus the integration baseline (to measure whether specialized protocols sacrifice general quality).

| Protocol | Integration | Adversarial | Stakeholder | Diagnostic | Exploration | Prioritization | Paradox | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1: Single | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| P2: Single+Context | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| P3: Synthesis | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| P4: Debate | ✓ | ✓ | ✓ | — | — | — | — | — |
| P5: Negotiate | ✓ | — | ✓ | — | — | — | — | — |
| P6: TRIZ | — | — | — | — | — | — | — | ✓ |
| P7: Wicked Qs | — | — | — | — | — | — | ✓ | — |
| P12: 25/10 | — | — | — | — | — | ✓ | — | — |
| P14: 1-2-4-All | — | — | — | — | ✓ | — | — | — |
| P16: ACH | — | — | — | ✓ | — | — | — | — |
| P22: Sequential | ✓ | — | — | — | — | — | — | — |

**Total runs:** ~180 (varies with protocol × question combinations)

### Run Protocol

1. Run all protocols × questions at T0 (no tools) first — establishes clean baseline
2. Run tool-eligible combinations at T1 (read-only retrieval)
3. Run phase-gated combinations (T0→T1 within a single run)
4. All outputs persisted in JSON + double-blind markdown format

### Analysis Framework

For each problem type, answer:

1. Which protocol scored highest on the problem-type-specific dimensions?
2. Which protocol scored highest on the universal dimensions?
3. Is there a protocol that dominates on both? If not, what's the trade-off?
4. Did tool access change the winner? At what cost?
5. Does the specialized protocol beat synthesis? By how much? At what cost multiple?

**Phase 2 Deliverable:** Complete scoring data for ~180 runs. Per-problem-type winner identification. Tool-access effect sizes by problem type. Cost-quality Pareto frontier for each problem type.

---

### Phase 3: Extended Protocols (Weeks 9-12)

**Goal:** Implement remaining protocols and test emergence mechanisms.

### Week 9-10: Implement 6 More Protocols

| Priority | Protocol | Why Now |
| --- | --- | --- |
| 7 | **P10: HSR** | Tests cross-functional translation as emergence mechanism |
| 8 | **P17: Red/Blue/White** | More structured adversarial protocol; compares to debate |
| 9 | **P21: Interests-Based Negotiation** | Upgrades negotiate mode with interest/BATNA layer |
| 10 | **P18: Delphi** | Tests estimation/forecasting problem type |
| 11 | **P26: Crazy Eights** | Tests constrained generation hypothesis |
| 12 | **P24: Causal Loop Mapping** | Tests systemic problem type |

### Week 10-11: Write Phase 3 Questions

- 4 questions each for: Sequential, Empathy, Estimation, Systemic problem types (16 new questions)
- Total question bank: 48 questions across 12 problem types

### Week 11-12: Phase 3 Evaluation Runs

- Test new protocols against their target types + integration baseline
- Compare HSR vs. Synthesis on exploration and diagnostic problems
- Compare Red/Blue/White vs. TRIZ on risk problems
- Compare Interests-Based Negotiation vs. Constraint Negotiation on stakeholder tension
- Compare Delphi vs. 25/10 on prioritization (estimation angle vs. ranking angle)

**Phase 3 Deliverable:** 17 total protocols tested. 48 benchmark questions across 12 problem types. Emergence mechanism analysis: which LS patterns produced surprising outputs?

---

### Phase 4: Emergence Testing (Weeks 13-16)

**Goal:** Specifically test whether LS-derived protocols produce emergent behavior that convergent protocols don't.

### Emergence Detection Methodology

Define "emergence" operationally for LLM agents:

1. **Novel synthesis:** Output contains an insight or recommendation that doesn't appear in any individual agent's independent response
2. **Frame shift:** The final output reframes the problem differently than any individual agent framed it
3. **Unexpected alliance:** Agents that should disagree (per their role prompts) converge on a shared position that isn't the obvious compromise
4. **Generative surprise:** Human reviewer rates the output as "I wouldn't have thought of that" (binary judgment, not scored)

### Emergence Comparison Pairs

| Pair | LS Protocol | Convergent Protocol | Problem Type | Hypothesis |
| --- | --- | --- | --- | --- |
| 1 | P14: 1-2-4-All | P3: Synthesis | Exploration | Progressive aggregation produces more novel output than parallel-then-combine |
| 2 | P10: HSR | P4: Debate | Diagnostic | Cross-functional translation produces more frame shifts than rebuttal |
| 3 | P7: Wicked Qs | P5: Negotiate | Paradox | LS sharpens tension; negotiate prematurely resolves it |
| 4 | P6: TRIZ | P17: Red/Blue/White | Risk | Inversion frame produces different failure modes than adversarial attack |
| 5 | P26: Crazy Eights | P14: 1-2-4-All | Exploration | Token constraint produces more diverse output than progressive aggregation |
| 6 | P12: 25/10 | P20: Borda Count | Prioritization | Iterative cross-scoring produces different consensus than formal voting |

**Phase 4 Deliverable:** Emergence rate data for LS vs. convergent protocols. Evidence for/against the hypothesis that constraint-induced reframing translates to LLM agents. Evidence for/against the hypothesis that social contagion can be architecturally approximated.

---

### Phase 5: Router Construction (Weeks 17-20)

**Goal:** Build the adaptive routing system that selects protocol, tool level, and evaluation rubric automatically.

### Router Architecture

`Input Question
    ↓
[Problem Type Classifier] → Integration | Adversarial | Stakeholder | Diagnostic | ...
    ↓
[Protocol Selector] → maps problem type to optimal protocol based on Phase 2-4 empirical data
    ↓
[Tool-Access Selector] → maps problem type to T0/T1/T2 + phase-gating rules
    ↓
[Evaluation Rubric Selector] → injects correct 3 specialized dimensions
    ↓
[Orchestrator] → runs selected protocol with selected tool level
    ↓
[Judge] → scores with selected rubric
    ↓
[Output] → recommendation + structural trace + quality score + cost`

### Problem Type Classifier Design

- Input: raw strategic question text
- Output: problem type classification + confidence
- Implementation: Haiku call with few-shot examples from the benchmark question bank
- Edge case: questions that span multiple types get routed to the protocol that handles the dominant type, with a flag for secondary type

### Protocol Selection Rules

Based on Phase 2-4 data, build a decision table:

`IF problem_type == diagnostic AND tools_available:
    protocol = ACH
    tool_level = T2
ELIF problem_type == diagnostic AND NOT tools_available:
    protocol = HSR  (or ACH at T0, depending on Phase 2 results)
    tool_level = T0
ELIF problem_type == exploration:
    protocol = 1-2-4-All  (or Crazy_Eights, depending on Phase 4 results)
    tool_level = T0
...`

This table is the core deliverable of the entire research program. Every cell is empirically grounded in benchmark data.

### Validation

- Hold out 2 questions per problem type from Phases 2-3 for router validation
- Run the router on held-out questions and compare its protocol selection to the empirically optimal protocol
- Measure: does the router select the top-1 protocol? Top-2? How often does it select a protocol that scores >0.5 points below optimal?

**Phase 5 Deliverable:** Working router integrated into C-Suite. Empirically-grounded decision table for protocol × tool-level selection. Validation accuracy on held-out questions.

---

### Phase 6: Simulation & Theoretical Validation (Weeks 21-24) — Optional

**Goal:** Use Agent-Based Modeling to explain empirical results, validate protocol rankings against network theory, and generate predictions for untested parameter combinations.

**Key work:**

- Model protocols as ABM simulations with simplified agent response functions (agreement tendency, novelty generation, persuadability)
- Map each protocol to its communication topology (chain, fully-connected, hierarchical clustering, etc.)
- Test Centola's complex contagion hypothesis: do protocols with reinforcement dynamics (Debate, 1-2-4-All) outperform single-pass protocols (Synthesis) because of network structure?
- Sensitivity analysis: identify which protocol parameters matter most (agent count, round count, topology) via simulation before additional LLM runs
- Validate: compare ABM-predicted protocol rankings against Phase 2-4 empirical rankings

**Phase 6 Deliverable:** Simulation framework, theoretical explanation of top protocol performance patterns, predictions for untested configurations, publishable paper connecting coordination protocols to network science.

---

## Part 6: Cost and Timeline Estimates

### Estimated API Costs Per Phase

| Phase | Runs | Est. Cost/Run (T0) | Est. Cost/Run (T1) | Total Est. |
| --- | --- | --- | --- | --- |
| Phase 1 (build) | ~30 pilot runs | $0.10-0.60 | N/A | ~$15 |
| Phase 2 (core eval) | ~180 | $0.10-1.00 | $0.50-5.00 | ~$200-400 |
| Phase 3 (extended) | ~120 | $0.10-1.00 | $0.50-5.00 | ~$150-300 |
| Phase 4 (emergence) | ~60 | $0.10-1.00 | N/A | ~$30-60 |
| Phase 5 (router) | ~40 validation | $0.10-1.00 | $0.50-5.00 | ~$50-100 |
| Phase 6 (simulation) | N/A (compute-only) | N/A | N/A | ~$0 |
| **Total** | **~430** |  |  | **~$450-875** |

Note: Costs assume v2-style tool-controlled runs dominate. If T2 runs reintroduce the v1 tool-calling overhead, the ceiling could reach $1,500-2,000.

### Timeline Summary

| Phase | Weeks | Deliverable |
| --- | --- | --- |
| 1: Foundation | 1-4 | 6 new protocols + 32 questions + eval infrastructure |
| 2: Core Evaluation | 5-8 | Primary test matrix results (~180 runs) |
| 3: Extended Protocols | 9-12 | 17 protocols + 48 questions + extended results |
| 4: Emergence Testing | 13-16 | LS vs. convergent emergence comparison |
| 5: Router Construction | 17-20 | Working adaptive router in C-Suite |
| 6: Simulation & Validation (optional) | 21-24 | ABM framework + theoretical validation + network science paper |

**Total: 24 weeks / 6 months to full research program completion (20 weeks core + 4 weeks optional simulation phase).**

---

## Part 7: Publication and Positioning

### Research Outputs

This program produces at minimum 4 publishable artifacts:

1. **"Coordination Architecture Selection for Multi-Agent Strategic Advisory"** — the core empirical paper. Protocol × problem type × tool-access results across 430+ runs. Target: ODSC talk, arXiv preprint, or AI engineering blog series.
2. **"Do Liberating Structures Produce Emergence in LLM Agent Teams?"** — the Phase 4 emergence analysis. Novel contribution: first empirical test of which human facilitation mechanisms survive translation to artificial agents. Target: academic venue or high-quality AI research blog.
3. **"The Adaptive Router: Empirically-Grounded Protocol Selection for Multi-Agent Systems"** — the Phase 5 engineering paper. Practical contribution: a working system that matches problems to coordination architectures. Target: engineering blog, open-source release, or product documentation for C-Suite.
4. **"Communication Topology and Complex Contagion in Multi-Agent Coordination"** — the Phase 6 simulation paper. Connects Centola's network science to LLM agent coordination: why reinforcement-based protocols (Debate, 1-2-4-All) outperform single-pass architectures, explained through ABM and communication topology analysis. Target: computational social science venue or network science journal.

### Competitive Positioning

No one in the multi-agent space has published this kind of systematic, empirically-grounded comparison across coordination architectures and problem types. CrewAI, AutoGen, and LangGraph all assume you choose your architecture up front. Cardinal Element's contribution is the **adaptive selection layer** — and the research program that justifies it.

---

## Appendix: Protocol Implementation Sketches

### P6: TRIZ Inversion

`Input: Strategic plan (already decided)
Agents: 3-5, all same role: "Failure Analyst"
System prompt: "Your job is to guarantee this plan fails.
  What would you do to ensure failure? Be specific."
Round 1: Each agent independently generates 5 failure modes
Round 2: Agents see all failure modes, identify which are
  redundant vs. genuinely distinct
Round 3: Facilitator agent ranks by severity × likelihood
Output: Ranked failure mode list with mitigation suggestions`

### P7: Wicked Questions

`Input: Strategic tension
Agents: 3 (functional roles) + 1 Facilitator
System prompt per agent: "Articulate this paradox from your
  perspective. Do NOT resolve it. Sharpen it."
Round 1: Each agent states the paradox in functional terms
Round 2: Facilitator identifies the sharpest formulation
Round 3: Agents propose boundary conditions ("the paradox
  tips toward X when..., tips toward Y when...")
Output: Sharpest paradox statement + boundary condition map`

### P14: 1-2-4-All Progressive Aggregation

`Input: Open-ended strategic question
Agents: 4+ (functional roles)
Round 1 (Solo): Each agent generates independently (no visibility)
Round 2 (Pairs): Agent A+B combine, Agent C+D combine
  (each pair sees both solo outputs, must build on both)
Round 3 (Quad): All 4 agents' pair outputs combined
  (quad sees both pair outputs, must build on both)
Round 4 (Synthesis): Final pass produces recommendation
Output: Progressive trace showing idea evolution
Structural artifact: Which solo ideas survived to final?`

### P16: Analysis of Competing Hypotheses

`Input: Diagnostic question (something is underperforming)
Agents: 4 (each champions one hypothesis)
Step 1: Facilitator generates 4 plausible hypotheses
Step 2: Each agent gathers evidence for/against ALL hypotheses
  (not just their own)
Step 3: Facilitator builds consistency matrix:
  [Hypothesis × Evidence] → Consistent / Inconsistent / N/A
Step 4: Eliminate hypotheses with most inconsistent evidence
Step 5: Surviving hypotheses ranked by remaining evidence weight
Output: Ranked hypotheses + consistency matrix + key evidence`

### P22: Sequential Pipeline

`Input: Strategic question with causal dependencies
Agent order: CFO → CTO → CMO (or customized per question)
Step 1: CFO receives question, produces financial analysis
Step 2: CTO receives question + CFO's full output,
  produces technical analysis that builds on CFO's conclusions
Step 3: CMO receives question + CFO output + CTO output,
  produces market/positioning analysis that builds on both
Step 4: Synthesis pass combines (but the sequential constraint
  means downstream agents already incorporated upstream thinking)
Output: Final recommendation with dependency trace
Structural artifact: What did each agent change based on upstream?`

---

*The Coordination Lab — Cardinal Element Research Program v1.0February 2026*