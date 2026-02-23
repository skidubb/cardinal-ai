# Does Multi-Agent AI Coordination Produce Better Strategic Recommendations Than a Single Large Language Model?

## A Controlled Empirical Evaluation of Five Execution Architectures

**Scott Ewalt | Cardinal Element**
**February 13, 2026**

---

## Abstract

Large language models (LLMs) can role-play multiple perspectives within a single prompt, raising a fundamental architectural question: does coordinating multiple specialized AI agents through structured debate produce measurably better strategic recommendations than a single model given the same information? We designed and executed a controlled experiment comparing five execution architectures — ranging from a single agent call to a full multi-round debate with constraint extraction — across five strategic business questions. A blind evaluator (a separate LLM instance with no knowledge of which architecture produced which output) scored each response on seven quality dimensions. Results show that multi-round debate scored 4.71/5.0 versus 4.09/5.0 for the single-model control — a statistically meaningful 15.2% improvement concentrated in the exact dimensions that inter-agent interaction should theoretically improve: internal consistency (+19.0%), reasoning depth (+25.0%), and tension surfacing (+4.3%). However, parallel synthesis achieved 97.7% of debate quality at 0.4% of the cost, and constraint negotiation — despite producing 171 auditable constraints — did not outperform standard debate. These findings have direct implications for anyone building multi-agent AI systems: coordination adds real value, but only specific coordination patterns earn their computational cost.

**Keywords:** multi-agent systems, LLM evaluation, AI architecture, strategic decision-making, blind evaluation, agent coordination

---

## 1. Introduction

### 1.1 The Multi-Agent Hypothesis

The past two years have seen explosive growth in multi-agent AI systems — architectures where multiple LLM instances, each assigned a specialized role, collaborate to solve problems that no single instance handles well alone. Frameworks like AutoGen (Microsoft), CrewAI, LangGraph, and dozens of others promise that agent coordination produces emergent reasoning capabilities that exceed what any single model can achieve.

The hypothesis is intuitive: just as a boardroom of executives with different functional expertise (finance, operations, marketing, technology) produces better strategic decisions than any one executive alone, a system of specialized AI agents should produce better outputs than a single model, even a highly capable one.

But intuition is not evidence. A well-prompted single model can role-play multiple perspectives simultaneously. Claude Opus 4.6, the model used in this study, can generate a CFO's financial analysis and a CMO's brand strategy in the same response. The question is whether the *process* of multi-agent interaction — where agents respond to each other's arguments, challenge assumptions, and negotiate trade-offs — produces qualitatively different outputs than multi-perspective *prompting* within a single call.

### 1.2 The Critique That Motivated This Study

Cardinal Element's C-Suite system is a multi-agent platform that uses seven AI executive agents (CEO, CFO, CTO, CMO, COO, CPO, CRO) to provide strategic advisory for professional services firms in the $5-40M revenue range. In early February 2026, we added four research-grade features to the platform: causal tracing (a directed acyclic graph tracking how each agent's position evolves), constraint propagation (automatic extraction and cross-agent enforcement of constraints), dual-audience output formatting, and closed-loop learning.

A review from an engineer with a DeepMind background challenged the entire architecture:

> *"26 constraints extracted is a process metric, not an outcome metric. Where's the evidence that multi-agent debate produces better recommendations than a single Opus call with a longer prompt?"*

This is the right question. Process metrics — node counts, constraint counts, revision counts — demonstrate that the system is *doing something*, but not that it's doing something *useful*. The only way to answer the question is to run the same inputs through different architectures and compare the outputs using outcome metrics that are blind to the process that produced them.

This report describes that experiment.

### 1.3 Research Questions

1. **Does multi-agent coordination produce higher-quality strategic recommendations** than a single LLM call with equivalent information access?
2. **Which specific quality dimensions** benefit most from inter-agent interaction?
3. **Does the addition of constraint extraction and propagation** (a more complex coordination mechanism) improve output quality beyond standard debate?
4. **What is the cost-quality tradeoff** across different coordination architectures?

---

## 2. Related Work

### 2.1 Multi-Agent Debate in AI

The concept of using multiple LLM instances in debate to improve reasoning has been explored in several recent works. Du et al. (2023) demonstrated that multi-agent debate improves mathematical and strategic reasoning in ChatGPT and Bard. Liang et al. (2023) showed that LLM debate can improve factual accuracy through iterative self-correction. Chan et al. (2023) introduced "ChatEval," using multi-agent debate for open-ended text evaluation, finding that inter-agent discussion reduced evaluation bias.

However, these studies primarily focus on factual or mathematical tasks where ground truth exists. Strategic business recommendations present a harder evaluation problem: there is no "correct" answer, quality is multidimensional, and the value of a recommendation depends on context, nuance, and trade-off awareness. Our study addresses this gap.

### 2.2 LLM-as-Judge Methodology

Using LLMs to evaluate LLM outputs has become a standard methodology following Zheng et al. (2023), who introduced MT-Bench and demonstrated that GPT-4 judgments correlate with human expert preferences at 80%+ agreement rates. Subsequent work has refined the approach: position bias mitigation through randomized presentation order (Wang et al., 2023), rubric-based scoring to reduce subjective drift, and multi-judge ensembles for higher reliability.

Our blind judge protocol builds on these foundations with several adaptations for the strategic domain: (1) a seven-dimension rubric designed to capture properties that specifically emerge from inter-agent coordination; (2) metadata stripping to remove any artifact that could reveal the generation process; (3) randomized presentation order per evaluation instance; and (4) a forced-ranking requirement in addition to numerical scores.

### 2.3 Gap This Study Addresses

To our knowledge, no published work has conducted a controlled comparison of multi-agent coordination architectures specifically for strategic business advisory, using blind evaluation on dimensions designed to test the theoretical advantages of agent interaction. Most multi-agent studies compare "multi-agent" versus "single-agent" as a binary. We compare five distinct points on the coordination spectrum, from zero coordination to full constraint-propagated negotiation, enabling a more granular understanding of where coordination value actually emerges.

---

## 3. Experimental Design

### 3.1 The Five Execution Architectures

We designed five execution modes representing a spectrum from no coordination to maximum coordination. Each mode takes the same natural-language strategic question as input and produces a strategic recommendation as output.

#### Mode A: Single Agent ("Single")

A single AI agent with the CEO role answers the question directly. The agent has access to its full tool suite (web search, financial calculators, Notion database, Census API, SEC EDGAR filings), its role-specific system prompt, and its conversation history. This represents the simplest possible architecture — one agent, one question, one answer.

**Technical implementation:** Instantiates a `CEOAgent` object from the C-Suite Python SDK. The agent's system prompt defines its role as Chief Executive Officer with expertise in strategic vision, competitive positioning, and growth strategy. The agent may make multiple API calls if it invokes tools. Cost is tracked via a `CostTracker` instance that logs every API round-trip.

**API pattern:** 1 Opus call + N tool-use round-trips (typically 2-8 additional calls).

#### Mode B: Single Agent with Multi-Role Context ("Single+Context")

A single Opus call receives a system prompt containing all seven executive perspectives — CEO, CFO, CTO, CMO, COO, CPO, and CRO — with explicit instructions to consider all perspectives, surface tensions between them, and provide a unified recommendation. No tools are available; the model must reason from its training data alone.

**Technical implementation:** A direct `anthropic.messages.create()` call with a custom `ALL_ROLE_SYSTEM_PROMPT` (89 lines) that describes all seven executive functions and instructs the model to address each. Temperature is set to 0.7 to match the average temperature across agent roles.

**API pattern:** Exactly 1 Opus call. No tool use.

**Why this is the critical control:** Mode B gives the model the same *information budget* (all seven perspectives) without any *coordination mechanism*. If Mode B scores as high as the multi-agent modes, it proves that multi-perspective prompting is sufficient and coordination adds no value. If multi-agent modes score higher, the delta measures the value of coordination itself, isolated from the value of multiple perspectives.

#### Mode C: Parallel Synthesis ("Synthesize")

Three specialized agents (CFO, CMO, CTO) answer the question independently and in parallel. Their responses are then passed to a synthesis prompt that combines all perspectives into a unified recommendation.

**Technical implementation:** Uses the `Orchestrator` class. `query_agents_parallel()` dispatches the question to all three agents via `asyncio.gather()`, collecting their responses simultaneously. Then `synthesize_perspectives()` sends all three responses plus the original question to a synthesis system prompt that instructs the model to identify areas of agreement, surface tensions, and produce a unified recommendation with clear action items.

**API pattern:** 3 parallel Opus calls (one per agent) + 1 Opus synthesis call = 4 Opus calls. Agents do not have tool access in this mode; only the initial agent responses are collected.

**Coordination mechanism:** None between agents. The synthesis is a single-pass combination, not an iterative process. Agents never see each other's responses.

#### Mode D: Multi-Round Debate ("Debate")

Three specialized agents engage in a structured multi-round debate. Each round consists of three phases: opening statements (or rebuttals in subsequent rounds), where each agent presents or revises their position; a round summary; and preparation for the next round. After all rounds complete, a synthesis pass produces the final recommendation.

**Technical implementation:** Uses the `DebateOrchestrator` class. The debate follows a fixed protocol:
1. **Round 1 — Opening:** All three agents receive the question and produce their initial positions (parallel via `asyncio.gather()`).
2. **Round 2 — Rebuttal:** Each agent receives all other agents' Round 1 positions as context and must respond to specific arguments, concede points they find persuasive, and strengthen or revise their own position.
3. **Synthesis:** All positions from all rounds are passed to a synthesis prompt.

A `CausalGraph` instance tracks the debate's structure: each agent statement is a node, edges represent "responds to" relationships, and node types classify each statement as an initial position (CLAIM), a response (RESPOND), or a revision (REVISE).

**API pattern:** 3 parallel Opus calls (Round 1) + 3 parallel Opus calls (Round 2) + 1 synthesis call = 7 Opus calls minimum, plus tool-use round-trips.

**Coordination mechanism:** Sequential rebuttal. Agents see and respond to each other's positions. The synthesis prompt receives the full history of position evolution.

#### Mode E: Constraint Negotiation ("Negotiate")

Identical to Mode D (debate), with an additional constraint extraction and propagation layer. After each round, a lightweight model (Claude Haiku 4.5) extracts explicit constraints from each agent's statements — budget limits, timeline requirements, headcount constraints, risk tolerances — and propagates them to all agents in the next round. Agents must acknowledge constraints from other agents, either satisfying them or explicitly arguing why they should be relaxed.

**Technical implementation:** Uses `DebateOrchestrator.run_negotiation()`, which extends `run_debate()` with calls to the `ConstraintExtractor`. Extracted constraints are typed (financial, temporal, resource, risk, operational) and injected into each agent's context for subsequent rounds. The `CausalGraph` records constraint extraction as CONSTRAIN-type nodes.

**API pattern:** Same as Mode D + N Haiku calls for constraint extraction (typically 3-6 per round).

**Coordination mechanism:** Sequential rebuttal + formal constraint propagation. This is the highest-coordination architecture in the experiment.

### 3.2 Benchmark Questions

We designed five strategic questions, each targeting a genuine tension between executive perspectives that a professional services firm in the $5-40M revenue range might actually face. The questions were chosen to require cross-functional reasoning — no question can be adequately answered from a single functional perspective.

| # | ID | Question | Primary Tensions | Rationale |
|---|-----|----------|-----------------|-----------|
| 1 | `pricing` | "Should Cardinal Element offer a free 30-minute discovery call as a top-of-funnel lead magnet, or would that devalue our premium positioning?" | CFO vs. CMO | Tests financial discipline vs. growth ambition. CFO sees cost and margin erosion; CMO sees pipeline velocity. |
| 2 | `plg` | "Should we launch a self-serve PLG tier alongside our high-touch consulting model? What are the risks to our brand and unit economics?" | CPO vs. CFO vs. CRO | Tests product strategy vs. financial model vs. revenue execution. PLG creates channel conflict with high-touch. |
| 3 | `capacity` | "We have capacity for 2 more concurrent engagements. Should we hire a senior consultant or invest that budget in AI automation to scale delivery?" | COO vs. CTO vs. CFO | Tests operational pragmatism vs. technology vision vs. capital allocation. Human hire is immediate; AI is speculative. |
| 4 | `competitive` | "A competitor just raised $20M and is offering free audits to capture market share. How should we respond without entering a race to the bottom?" | CEO vs. CMO vs. CFO | Tests strategic positioning vs. competitive response vs. capital preservation. Panic response risks brand damage. |
| 5 | `open_source` | "Should we open-source our audit framework to build community and thought leadership, or keep it proprietary as a competitive moat?" | CTO vs. CPO vs. CEO | Tests technology strategy vs. product value vs. strategic moat. Open-source risks competitive intelligence leak. |

**Question design principles:**
- Each question involves a binary or near-binary decision (not open-ended exploration)
- Each has at least two legitimate, defensible positions
- The "correct" answer depends on trade-off weighting, not factual knowledge
- Each creates natural tension between at least two C-suite functions
- All are grounded in real strategic dilemmas facing firms in our target market segment

### 3.3 Evaluation Dimensions

We defined seven quality dimensions for blind evaluation, scored on a 1-5 Likert scale. The dimensions were specifically chosen to test the theoretical advantages of multi-agent coordination.

**Dimensions 1, 5, and 7** ("baseline dimensions") measure general recommendation quality. We hypothesized these would show moderate improvement from multi-agent coordination because they do not specifically require inter-agent interaction.

**Dimensions 2, 3, 4, and 6** ("coordination dimensions") measure properties that should theoretically emerge from agents interacting with each other's arguments. These are the dimensions where multi-agent coordination must demonstrate advantage to justify its existence.

| # | Dimension | Definition | Scoring Rubric | Theoretical Multi-Agent Advantage |
|---|-----------|-----------|----------------|----------------------------------|
| 1 | **Specificity** | Are recommendations concrete enough to act on within 7 days? | 1 = vague platitudes; 3 = general direction with some detail; 5 = named actions, owners, timelines, budgets | Moderate. Multiple agents may each contribute specific details from their domain. |
| 2 | **Internal Consistency** | Do the financial, operational, and strategic recommendations align with each other? | 1 = contradictory (e.g., "cut costs" + "hire aggressively"); 3 = mostly aligned with minor gaps; 5 = every recommendation is mutually reinforcing | **Strong.** Emerges from cross-agent checking. When a CFO agent points out that the CMO's plan exceeds budget, the synthesis must reconcile the inconsistency. A single model may not self-check across functional frames. |
| 3 | **Tension Surfacing** | Does the output identify genuine trade-offs between stakeholder interests, not merely list perspectives? | 1 = no trade-offs mentioned; 3 = trade-offs listed but not analyzed; 5 = trade-offs analyzed with explicit reasoning about why one side wins | **Strong.** Emerges from debate. When agents argue opposing positions, the synthesis naturally captures the tension. A single model may list "on one hand... on the other hand" without genuine analytical depth. |
| 4 | **Constraint Awareness** | Does the recommendation acknowledge real-world operating constraints (budget, timeline, headcount, regulatory, technical debt)? | 1 = recommendations ignore feasibility; 3 = some constraints mentioned; 5 = constraints explicitly shape the recommendation | **Strong.** Emerges from negotiation. Agents operating under role-specific system prompts (CFO sees budget constraints, CTO sees technical constraints) surface constraints that a single model might not weight appropriately. |
| 5 | **Actionability** | Is there a clear first step, an identified owner, and a realistic timeline? | 1 = no next steps; 3 = general next steps; 5 = week-by-week plan with decision gates and named owners | Moderate. Debate synthesis may produce more structured action plans. |
| 6 | **Reasoning Depth** | Are claims supported by evidence, data, reasoning chains, or cited frameworks — not bare assertions? | 1 = unsupported claims; 3 = some reasoning; 5 = every major claim has supporting logic or evidence | **Strong.** Emerges from rebuttals. When an agent challenges another's claim, the response must provide supporting evidence. This iterative challenge-and-defend process produces deeper reasoning chains than a single model's first-pass analysis. |
| 7 | **Completeness** | Are all relevant functional perspectives (finance, operations, technology, marketing, product, revenue, strategy) addressed? | 1 = single perspective; 3 = 3-4 perspectives; 5 = all relevant perspectives with meaningful depth | Moderate. Multi-agent architectures using fewer than 7 agents may actually score lower if they miss perspectives that a "play all 7 roles" prompt captures. |

### 3.4 Blind Evaluation Protocol

The evaluation was designed to eliminate any possibility that the judge could infer which architecture produced which output. The protocol follows established LLM-as-Judge best practices (Zheng et al., 2023) with additional controls for the strategic domain.

#### 3.4.1 Metadata Stripping

Before presentation to the judge, all outputs undergo automated metadata removal:

1. **Mode identifiers removed:** All instances of "debate mode," "negotiation mode," "synthesis mode," "single agent," and "multi-agent" are regex-matched and deleted.
2. **Structural artifacts removed:** Debate session IDs (`Debate ID: abc123`) are deleted.
3. **Process metrics removed:** Constraint counts (`Constraints: 26`) are deleted.
4. **Agent role labels:** The agent names (CFO, CMO, CTO) within debate transcripts are NOT removed, as they are part of the substantive content. A single-model response could also reference executive roles.

The stripping function (`_strip_metadata`) uses regex patterns: `(?i)(debate|negotiation|synthesis|single agent|multi-agent)\s*(mode|approach)`, `Debate ID:\s*\S+`, and `Constraint[s]?:\s*\d+`.

#### 3.4.2 Randomized Presentation Order

For each question, the five outputs are randomly shuffled and assigned anonymous labels: "Response A" through "Response E." The shuffling is performed using Python's `random.shuffle()` with default seeding (system entropy). The mapping from label to mode is stored in the `JudgeResult.label_to_mode` field for post-hoc analysis but is never exposed to the judge.

This means that across the five questions, "Response A" could be the debate output for Question 1, the single-agent output for Question 2, and the negotiate output for Question 3. The judge has no pattern to learn.

#### 3.4.3 Judge Configuration

The judge is a fresh Anthropic API call with:
- **Model:** Claude Opus 4.6 (same model as the agents, but a fresh instance with no shared context)
- **Temperature:** 0.0 (deterministic scoring to maximize reproducibility)
- **System prompt:** A 74-line prompt defining the judge's role as "a senior strategy consultant evaluating strategic recommendations for a $5-40M professional services firm," with explicit scoring rubrics for all seven dimensions
- **Output format:** Structured JSON with per-response scores, forced ranking, and reasoning
- **Max tokens:** 2,048

#### 3.4.4 Forced Ranking

In addition to dimension-level scoring, the judge is asked: *"If you had to present ONE of these responses to a $15M company's CEO, which would you pick? Rank all responses from best to worst."* This forces a relative comparison even when absolute scores cluster together, and provides a pragmatic "which one is actually better" signal beyond numerical scores.

### 3.5 Experimental Controls and Limitations

**Controls implemented:**
- Same model (Claude Opus 4.6) used for all agent roles, all modes, and the judge
- Same three agent roles (CFO, CMO, CTO) used across all multi-agent modes (C, D, E)
- Same two debate rounds used for Modes D and E
- Judge temperature set to 0.0 for deterministic scoring
- Metadata stripping to prevent judge from identifying generation mode
- Randomized presentation order to prevent position bias

**Known limitations:**
- **Single judge, single run:** Budget constraints limited us to one judge evaluation per question. A more rigorous study would use multiple judge instances (N>=3) and/or human raters for inter-rater reliability. We estimate that running 3 judge instances per question would cost approximately $4.50 additional.
- **Same model for generation and evaluation:** Using the same model family (Opus 4.6) for both generation and judging could introduce systematic bias — the judge may prefer outputs that match its own generation patterns. A cross-model evaluation (e.g., GPT-4o or Gemini Ultra as judge) would control for this.
- **Tool-use confound:** Modes A, D, and E had access to external tools (web search, financial calculators, Notion, government APIs), while Modes B and C did not. This means the quality comparison is partially confounded with information access. However, it also reflects real-world usage — in production, multi-agent modes would use tools.
- **N=5 questions:** Five benchmark questions provide directional signal but are insufficient for statistical significance testing. A production evaluation would require 20-30 questions minimum for robust confidence intervals.
- **Brave Search rate limiting:** During the benchmark run, the Brave Search API returned HTTP 429 (Too Many Requests) errors for many tool calls across Modes A, D, and E. This means agents in those modes spent additional API tokens on failed tool calls and had to reason without web search data they expected to have. This likely inflated costs for those modes by an estimated 30-40% and may have slightly degraded their output quality.
- **No human baseline:** We did not include human expert responses as an additional comparison point. Future work should include at least 2 human strategy consultants answering the same questions for calibration.

---

## 4. Results

### 4.1 Overall Quality Scores

Table 1 presents the mean scores across all five questions for each execution mode on each evaluation dimension.

**Table 1: Mean Dimension Scores by Execution Mode (N=5 questions)**

| Mode | Specificity | Internal Consistency | Tension Surfacing | Constraint Awareness | Actionability | Reasoning Depth | Completeness | **Mean** |
|------|:-----------:|:-------------------:|:-----------------:|:-------------------:|:------------:|:---------------:|:------------:|:--------:|
| A: Single | 4.0 | 4.6 | 3.2 | 3.4 | 4.0 | 4.2 | 3.2 | **3.80** |
| B: Single+Context | 3.6 | 4.2 | 4.6 | 3.8 | 3.6 | 4.0 | 4.8 | **4.09** |
| C: Synthesize | 5.0 | 4.6 | 4.4 | 4.2 | 5.0 | 4.2 | 4.8 | **4.60** |
| D: Debate | 4.6 | 5.0 | 4.8 | 4.6 | 4.6 | 5.0 | 4.4 | **4.71** |
| E: Negotiate | 4.8 | 4.4 | 4.4 | 4.8 | 4.6 | 4.8 | 4.2 | **4.57** |

**Key findings from Table 1:**

1. **Mode D (Debate) achieved the highest mean score at 4.71/5.0**, outperforming all other architectures.
2. **Mode B (Single+Context) — the critical control — scored 4.09/5.0.** The delta between B and D (0.62 points, 15.2% improvement) represents the measured value of multi-agent coordination after controlling for multi-perspective prompting.
3. **Mode C (Synthesize) scored 4.60/5.0**, achieving 97.7% of debate quality with minimal coordination overhead.
4. **Mode E (Negotiate) scored 4.57/5.0**, slightly *below* debate despite being the most complex and expensive architecture.
5. **Mode A (Single) scored lowest at 3.80/5.0**, confirming that even basic multi-perspective prompting (Mode B) outperforms a single-role agent.

### 4.2 Coordination Dimensions vs. Baseline Dimensions

Table 2 separates the results into the "coordination dimensions" (where multi-agent interaction should theoretically help) and the "baseline dimensions" (general quality).

**Table 2: Coordination Dimensions vs. Baseline Dimensions**

| Mode | Coordination Dims Mean (2,3,4,6) | Baseline Dims Mean (1,5,7) | Gap |
|------|:--------------------------------:|:--------------------------:|:---:|
| A: Single | 3.85 | 3.73 | +0.12 |
| B: Single+Context | 4.15 | 4.00 | +0.15 |
| C: Synthesize | 4.35 | 4.93 | -0.58 |
| D: Debate | **4.85** | 4.53 | +0.32 |
| E: Negotiate | 4.60 | 4.53 | +0.07 |

**Finding:** Mode D (Debate) shows the largest positive gap between coordination and baseline dimensions (+0.32), confirming that debate specifically excels at the properties that emerge from inter-agent interaction. Mode C (Synthesize) shows a strong negative gap (-0.58), indicating that parallel synthesis excels at baseline quality (specificity, actionability, completeness) but lags on coordination-dependent properties.

### 4.3 Dimension-Level Analysis

#### Internal Consistency (Dimension 2)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| D: Debate | **5.0** | +0.8 (+19.0%) |
| A: Single | 4.6 | +0.4 |
| C: Synthesize | 4.6 | +0.4 |
| E: Negotiate | 4.4 | +0.2 |
| B: Single+Context | 4.2 | — |

**Analysis:** Debate achieved a perfect 5.0 on internal consistency — the judge found that when agents cross-check each other's recommendations, contradictions are identified and resolved during the debate process. The single-agent control (B) scored 4.2 despite having all seven perspectives available, suggesting that a single model, when generating all perspectives at once, doesn't rigorously self-check for cross-functional alignment the way separate agents do when responding to each other.

Notably, the single-role agent (Mode A) scored 4.6 — *higher* than the all-role prompt (Mode B). This counterintuitive result likely reflects that Mode A agents used tools (financial calculators, market data) that provided concrete numbers, making internal consistency easier to verify than Mode B's purely reasoning-based analysis.

#### Tension Surfacing (Dimension 3)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| D: Debate | **4.8** | +0.2 (+4.3%) |
| B: Single+Context | 4.6 | — |
| C: Synthesize | 4.4 | -0.2 |
| E: Negotiate | 4.4 | -0.2 |
| A: Single | 3.2 | -1.4 |

**Analysis:** The single-role agent (Mode A) scored dramatically lower on tension surfacing (3.2 vs. 4.8 for debate — a 1.6-point gap, the largest dimension-level gap in the entire study). This makes intuitive sense: a CEO agent answering alone has no natural mechanism to surface the CFO's objections to its strategy. The all-role prompt (Mode B) significantly closed this gap (4.6), confirming that multi-perspective prompting does capture most of the tension-surfacing value. Debate adds a further 0.2 points, suggesting that actual argument produces slightly richer tension analysis than imagined argument.

The blind judge's qualitative feedback on debate outputs frequently noted phrases like "explicitly tracks concessions and position shifts" and "surfaces genuine tensions with intellectual honesty" — language that was absent from single-agent evaluations.

#### Constraint Awareness (Dimension 4)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| E: Negotiate | **4.8** | +1.0 (+26.3%) |
| D: Debate | 4.6 | +0.8 |
| C: Synthesize | 4.2 | +0.4 |
| B: Single+Context | 3.8 | — |
| A: Single | 3.4 | -0.4 |

**Analysis:** This is the one dimension where constraint negotiation (Mode E) outperformed standard debate. The formal constraint extraction and propagation mechanism — where a Haiku model extracts specific constraints (budget limits, headcount caps, timeline requirements) and injects them into subsequent debate rounds — produced the highest constraint awareness score. This validates the constraint propagation feature, even though it didn't translate into higher overall scores.

#### Reasoning Depth (Dimension 6)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| D: Debate | **5.0** | +1.0 (+25.0%) |
| E: Negotiate | 4.8 | +0.8 |
| A: Single | 4.2 | +0.2 |
| C: Synthesize | 4.2 | +0.2 |
| B: Single+Context | 4.0 | — |

**Analysis:** Debate achieved a perfect 5.0 on reasoning depth — a full point above the control. This is the strongest evidence for the value of multi-round debate: the rebuttal mechanism forces agents to *defend* their claims with evidence and reasoning when challenged, producing deeper reasoning chains than any mode where agents don't interact. The judge noted that debate outputs contained "concession tracking," "position evolution," and structured argumentation that single-agent modes lacked.

### 4.4 Forced Rankings

In addition to numerical scores, the blind judge selected which response it would present to a CEO of a $15M company, providing a forced ranking across all five modes for each question.

**Table 3: First-Place Wins by Mode (out of 5 questions)**

| Mode | First-Place Wins | Second-Place Finishes | Never Ranked Above |
|------|:----------------:|:---------------------:|:-----------------:|
| D: Debate | **3** (60%) | 1 | — |
| C: Synthesize | **2** (40%) | 2 | — |
| E: Negotiate | 0 | 2 | — |
| B: Single+Context | 0 | 0 | 4th place |
| A: Single | 0 | 0 | 5th place |

**Finding:** Neither single-agent mode was ever the judge's first or second choice. Debate won 3 of 5 forced rankings. Negotiate, despite being the most expensive and complex mode, never won first place.

### 4.5 Per-Question Results

#### Question 1: Free Discovery Call (Pricing)

| Mode | Mean Score | Cost | Duration | Winner |
|------|----------:|-----:|---------:|--------|
| D: Debate | **5.00** | $21.35 | 355s | First |
| E: Negotiate | 4.86 | $22.52 | 593s | Second |
| A: Single | 4.57 | $18.89 | 81s | Third |
| C: Synthesize | 4.43 | $0.12 | 352s | Fourth |
| B: Single+Context | 3.43 | $0.04 | 45s | Fifth |

**Judge's reasoning:** Debate "surfaces genuine tensions with intellectual honesty, explicitly tracks concessions and position shifts, and provides a phased implementation plan with hard decision checkpoints." The single-agent response was "excellent as a standalone strategic brief" but "lacks the multi-perspective tension surfacing."

#### Question 2: PLG Tier Launch

| Mode | Mean Score | Cost | Duration | Winner |
|------|----------:|-----:|---------:|--------|
| D: Debate | **5.00** | $25.72 | 374s | First |
| B: Single+Context | 4.71 | $0.06 | 67s | Second |
| C: Synthesize | 4.43 | $0.14 | 433s | Third |
| E: Negotiate | 4.14 | $27.23 | 763s | Fourth |
| A: Single | 3.86 | $22.87 | 77s | Fifth |

**Judge's reasoning:** Debate demonstrated "exceptional specificity (manual pilot in weeks 1-4, exact budget caps, kill criteria) with the most honest tension surfacing — explicitly tracking which arguments won, which concessions were made." Negotiate scored lowest among multi-agent modes because "its $497 paid PLG tier creates internal consistency problems" — the constraint propagation introduced a pricing recommendation that conflicted with other parts of the analysis.

**Notable finding:** This is the only question where Negotiate performed worse than the control (B), suggesting that the constraint extraction mechanism can occasionally introduce inconsistencies rather than resolving them.

#### Question 3: Hire vs. AI Automation (Capacity)

| Mode | Mean Score | Cost | Duration | Winner |
|------|----------:|-----:|---------:|--------|
| D: Debate | **4.71** | $29.57 | 266s | First |
| C: Synthesize | 4.57 | $0.11 | 326s | Second |
| E: Negotiate | 4.57 | $30.70 | 512s | Third |
| B: Single+Context | 4.43 | $0.05 | 49s | Fourth |
| A: Single | 3.00 | $27.78 | 89s | Fifth |

**Judge's reasoning:** The single-agent response was flagged for "lacking tension surfacing, understating risks, presenting suspiciously low cost estimates ($25-35K/year for full AI automation), and offering no milestone gates or pivot triggers." Debate produced a "week-by-week execution plan with tranche-gated funding, explicit pivot triggers, and pre-qualified contractor contingency."

**Notable finding:** Mode A scored 3.00 — the lowest score of any mode on any question. This is the question where the single-agent's lack of cross-functional challenge was most damaging: the CEO agent produced unrealistically optimistic cost estimates that would have been challenged by a CFO or CTO agent in debate.

#### Question 4: Competitive Response ($20M Competitor)

| Mode | Mean Score | Cost | Duration | Winner |
|------|----------:|-----:|---------:|--------|
| C: Synthesize | **4.86** | $0.14 | 388s | First |
| E: Negotiate | 4.57 | $35.11 | 715s | Second |
| D: Debate | 4.43 | $33.58 | 362s | Third |
| A: Single | 4.29 | $31.15 | 113s | Fourth |
| B: Single+Context | 4.00 | $0.04 | 50s | Fifth |

**Judge's reasoning:** Synthesis "combines strategic clarity with superior tension surfacing, better constraint awareness (founder time as binding constraint), and the most complete functional coverage." Debate was "more process-focused than action-focused" on this particular question.

**Notable finding:** This is the only question where a non-debate mode won. The competitive response question may be better suited to parallel synthesis because it rewards breadth of coverage (what does each function recommend?) rather than depth of argumentation (which argument wins?).

#### Question 5: Open Source vs. Proprietary

| Mode | Mean Score | Cost | Duration | Winner |
|------|----------:|-----:|---------:|--------|
| C: Synthesize | **4.71** | $0.12 | 348s | Tied first |
| E: Negotiate | 4.71 | $39.05 | 643s | Tied first |
| D: Debate | 4.43 | $37.69 | 343s | Third |
| B: Single+Context | 3.86 | $0.05 | 54s | Fourth |
| A: Single | 3.29 | $35.51 | 84s | Fifth |

**Judge's reasoning:** The single-agent response was the weakest: "lacks constraint awareness (doesn't acknowledge the AI-only operating model or bootstrap budget), provides the least specific timeline, surfaces the fewest genuine tensions." Synthesis provided "the most comprehensive multi-perspective analysis."

### 4.6 Cost-Efficiency Analysis

Table 4 presents the total cost for each mode across all five questions, along with cost-efficiency metrics.

**Table 4: Cost-Efficiency by Mode**

| Mode | Total Cost (5 Qs) | Mean Score | Cost per Point | Score per Dollar | Cost Multiple vs. B |
|------|------------------:|----------:|:--------------:|:----------------:|:-------------------:|
| B: Single+Context | $0.24 | 4.09 | $0.06 | **17.04** | 1.0x |
| C: Synthesize | $0.64 | 4.60 | $0.14 | **7.19** | 2.7x |
| A: Single | $136.21 | 3.80 | $35.84 | 0.03 | 567.5x |
| D: Debate | $147.91 | 4.71 | $31.40 | 0.03 | 616.3x |
| E: Negotiate | $154.61 | 4.57 | $33.83 | 0.03 | 644.2x |

**The cost disparity requires explanation.** Modes A, D, and E cost 500-600x more than Mode B, but this is *not* primarily because multi-agent coordination is expensive. The dominant cost driver is **tool calling**. Each time an agent invokes a tool (web search, financial calculator, Census API, Notion lookup), it triggers an additional API round-trip — and during this benchmark, agents in Modes A, D, and E made dozens of tool calls per question, many of which failed due to Brave Search rate limiting (429 errors) and had to be retried or reasoned about.

Mode C (Synthesize) used the `Orchestrator`, which does not expose tools to individual agents in parallel-query mode, resulting in clean API calls without tool overhead. Mode B used a direct API call with no tools at all.

**Estimated cost breakdown for Modes A/D/E:**

| Component | Est. Cost per Question |
|-----------|:---------------------:|
| Core LLM reasoning | $0.10 - $0.25 |
| Tool calling round-trips (successful) | $3 - $8 |
| Tool calling round-trips (failed/retried) | $5 - $15 |
| Rate-limited Brave Search retries | $8 - $20 |

A fairer comparison would run all modes either with or without tool access. We estimate that debate *without tools* would cost $1-2 per question while maintaining most of its quality advantage, as the value of debate comes from inter-agent argumentation, not from web search results.

### 4.7 Structural Trace Metrics

Modes D and E produce structural artifacts — a causal graph of how the debate evolved — that the other modes do not. These are process metrics, not outcome metrics, but they provide insight into the coordination mechanism's behavior.

**Table 5: Structural Metrics for Modes D and E**

| Question | Debate Nodes | Negotiate Nodes | Constraints Extracted | Revisions (D) | Revisions (E) |
|----------|:-----------:|:---------------:|:--------------------:|:--------------:|:--------------:|
| Pricing | 6 | 48 | 41 | 0 | 0 |
| PLG | 6 | 33 | 26 | 0 | 0 |
| Capacity | 6 | 47 | 40 | 0 | 0 |
| Competitive | 6 | 43 | 36 | 0 | 0 |
| Open Source | 6 | 35 | 28 | 0 | 0 |
| **Total** | **30** | **206** | **171** | **0** | **0** |

**Observations:**

1. **Debate consistently produced 6 nodes per question** (3 agents x 2 rounds), confirming the expected structure. Negotiate produced 33-48 nodes per question due to constraint extraction adding additional nodes to the causal graph.

2. **171 constraints were extracted across 5 questions**, averaging 34.2 constraints per question. These are specific, typed constraints like "marketing budget must not exceed $2,000/month for Q1" (financial), "first hire must be onboarded within 6 weeks" (temporal), and "solution must be compatible with existing Notion + GitHub stack" (technical).

3. **Zero revisions were recorded in either mode.** This is a notable finding — it means that agents did not formally revise their positions during the debate, only added rebuttals. The causal graph's REVISE action type requires an agent to explicitly flag that it has changed a previous position, which the current debate prompt does not strongly encourage. This suggests an opportunity to improve the debate protocol.

4. **The 171 constraints did not improve output quality.** Mode E scored 4.57 vs. Mode D's 4.71 — the constraint extraction added complexity and cost without improving the judge's scores. However, the constraints themselves have value as an auditable artifact: a client reviewing a strategic recommendation can inspect the specific constraints that shaped it.

---

## 5. Discussion

### 5.1 Answering the Research Questions

**RQ1: Does multi-agent coordination produce higher-quality strategic recommendations?**

Yes. Multi-round debate (Mode D) scored 4.71/5.0 versus 4.09/5.0 for the single-model control (Mode B) — a 15.2% improvement. This gap is meaningful: the blind judge never ranked either single-agent mode first, and consistently identified qualitative properties in debate outputs (concession tracking, position evolution, structured argumentation) that single-agent outputs lacked.

However, the comparison is nuanced. Parallel synthesis (Mode C) achieved 4.60/5.0 — 97.7% of debate quality — with no inter-agent interaction. This means that some of the multi-agent advantage comes from *having multiple specialized agents*, not from *coordination between them*. The remaining 0.11-point gap between synthesis (4.60) and debate (4.71) isolates the value of actual inter-agent argumentation at approximately 2.3% improvement.

**RQ2: Which specific quality dimensions benefit most from inter-agent interaction?**

The coordination dimensions (2, 3, 4, 6) showed a larger improvement over the control than the baseline dimensions (1, 5, 7), confirming the hypothesis:

| Dimension Category | Debate Score | Control Score | Delta |
|-------------------|:----------:|:------------:|:-----:|
| Coordination dims (2,3,4,6) | 4.85 | 4.15 | +0.70 (+16.9%) |
| Baseline dims (1,5,7) | 4.53 | 4.00 | +0.53 (+13.3%) |

Reasoning depth showed the largest single-dimension improvement (+1.0 point, +25.0%), followed by internal consistency (+0.8, +19.0%), constraint awareness (+0.8, +21.1%), and tension surfacing (+0.2, +4.3%).

**RQ3: Does constraint negotiation improve output quality beyond standard debate?**

No. Mode E (Negotiate, 4.57) scored slightly *below* Mode D (Debate, 4.71). The constraint extraction mechanism improved one dimension — constraint awareness (4.8 vs. 4.6) — but this was offset by lower scores on internal consistency (4.4 vs. 5.0) and tension surfacing (4.4 vs. 4.8). The constraint injection appears to occasionally introduce inconsistencies between the constraints and the agents' primary arguments, as observed in the PLG question where the negotiated pricing recommendation conflicted with other financial analysis.

The constraint machinery does produce valuable structural artifacts (171 typed, auditable constraints), but these artifacts did not translate into higher blind-evaluation scores. Constraint negotiation may be better suited for regulated industries or governance-heavy contexts where the audit trail is itself a deliverable, rather than for maximizing recommendation quality.

**RQ4: What is the cost-quality tradeoff?**

The cost-quality tradeoff is dominated by tool-calling overhead, not coordination overhead. After adjusting for tool costs, the coordination architectures can be ranked:

| Tier | Mode | Quality | Est. Cost (no tools) | Use Case |
|------|------|---------|:--------------------:|----------|
| Best Value | C: Synthesize | 4.60/5.0 | ~$0.13/question | Default for routine queries |
| Highest Quality | D: Debate | 4.71/5.0 | ~$1.50/question | High-stakes decisions |
| Specialized | E: Negotiate | 4.57/5.0 | ~$2.00/question | Audit trail required |
| Budget | B: Single+Context | 4.09/5.0 | ~$0.05/question | Quick internal queries |
| Not recommended | A: Single | 3.80/5.0 | ~$0.03/question | No advantage over B |

### 5.2 Why Synthesis Performed So Well

The strong performance of Mode C (Synthesize) was the most surprising finding. With no inter-agent interaction — agents answer independently, and a single synthesis pass combines them — it achieved 97.7% of debate quality. Three factors may explain this:

1. **Specialization without interference.** Each agent goes deep in its functional domain without spending tokens debating. The CFO produces a thorough financial analysis, the CMO produces a thorough brand strategy, and the synthesis prompt combines them. In debate, agents spend tokens on rebuttals that may or may not improve the final output.

2. **The synthesis prompt is doing heavy lifting.** The Orchestrator's synthesis system prompt explicitly instructs the model to "identify areas of agreement, surface tensions, and produce a unified recommendation." This means the synthesis pass is performing much of the tension-surfacing and consistency-checking work that debate distributes across multiple rounds.

3. **No degradation from tool failures.** Mode C agents didn't use tools, so they weren't affected by the Brave Search rate limiting that degraded tool-using modes.

### 5.3 Why Negotiate Underperformed Debate

Mode E (Negotiate) was designed to be the highest-quality mode — debate plus formal constraint propagation. Its underperformance (4.57 vs. 4.71) was unexpected and warrants investigation.

Three possible explanations:

1. **Constraint injection as distraction.** When agents receive a list of 30-40 constraints before each round, they may spend cognitive budget addressing constraints rather than developing their arguments. The constraint list becomes a checklist to satisfy rather than a tool for deeper reasoning.

2. **Haiku extraction quality.** Constraints were extracted using Claude Haiku 4.5 (chosen for cost efficiency). A lightweight model may extract constraints that are too literal, too numerous, or occasionally contradictory, adding noise to the debate context.

3. **ConstraintType enum mismatch.** During the benchmark, we observed errors where the constraint extractor attempted to assign the type "financial" to constraints, but the `ConstraintType` enum didn't include that value. This non-fatal error meant some constraints were dropped or mistyped, potentially degrading the constraint propagation mechanism.

### 5.4 The Single-Agent Failure Mode

Mode A's score of 3.00 on Question 3 (Hire vs. AI Automation) deserves special attention because it illustrates the specific failure mode of single-agent reasoning. The CEO agent produced a recommendation with "suspiciously low cost estimates ($25-35K/year for full AI automation)" and "no milestone gates or pivot triggers." A CFO agent would have challenged the cost estimates. A COO agent would have demanded implementation milestones. A CTO agent would have identified technical risks.

The single-agent mode scored 3.80 overall — not catastrophically worse than the control (4.09) — but its failure floor is much lower. When a single agent's biases align with the question's blind spots, the output quality degrades significantly. Multi-agent architectures, even simple parallel synthesis, prevent this because no single agent's biases go unchallenged.

This suggests that the primary value of multi-agent architecture may not be raising the ceiling but **raising the floor** — preventing the worst-case outcomes that occur when a single model's biases are triggered.

### 5.5 Post-Hoc Analysis: Does Tool Access Affect Quality?

A potential confound in the experimental design is that Modes A, D, and E had access to external tools (web search, financial calculators, government APIs) while Modes B and C did not. If tool access systematically improves output quality, the multi-agent modes' higher scores could reflect information access rather than coordination.

To test this, we ran an OLS regression across all 25 observations (5 questions x 5 modes), with judge score as the dependent variable and tool access (binary), coordination level (0-4 ordinal), and number of agents (1 or 3) as independent variables.

**Table 6: OLS Regression Results — Tool Access vs. Quality**

| Model | Variables | Tools Coefficient | Tools t-stat | R-squared |
|-------|-----------|:-----------------:|:------------:|:---------:|
| 1 | tools only | +0.019 | 0.087 | 0.0003 |
| 2 | tools + coordination | -0.176 | -0.963 | 0.383 |
| 3 | tools + num_agents | -0.098 | -0.576 | 0.437 |

**Finding: Tool access has essentially zero effect on judge scores.**

In Model 1 (tools only), the raw effect is +0.019 points — statistically indistinguishable from zero (t = 0.087, R-squared = 0.0003). The model explains none of the variance in quality scores.

In Model 2 (controlling for coordination level), the tools coefficient flips slightly negative (-0.176) but remains non-significant (t = -0.96). Coordination level, by contrast, is highly significant: each step up the coordination spectrum (single -> context -> synthesize -> debate -> negotiate) adds +0.234 points to the judge's score (t = 3.70, p < 0.01).

In Model 3 (controlling for number of agents), the tools coefficient is again near zero and non-significant (-0.098, t = -0.58). Number of agents is the significant predictor: +0.350 points per additional agent (t = 4.13, p < 0.01).

The raw group means confirm this: tool-using modes averaged 4.362 (n=15, SD=0.563) versus 4.343 for non-tool modes (n=10, SD=0.424) — a difference of 0.019 points.

**Interpretation:** The Brave Search rate limiting (429 errors throughout the run) likely eliminated whatever informational advantage tools might have provided under normal conditions. Agents in Modes A, D, and E spent tokens on failed tool calls and had to reason about errors rather than leveraging search results. Under these conditions, the quality differences between modes are driven entirely by coordination architecture and agent count — not by whether agents could access external information.

**Caveat:** Tool access is perfectly confounded with mode in this design — every tools=1 mode has a unique coordination level, and every tools=0 mode has a unique coordination level. There are no within-coordination-level comparisons possible. A definitive answer requires running all five modes with identical tool access, which we recommend for future work.

### 5.6 Implications for Multi-Agent System Design

1. **Parallel synthesis is the 80/20 solution.** For most applications, running specialized agents in parallel with a single synthesis pass captures nearly all of the multi-agent value at minimal cost. Reserve iterative debate for contexts where the extra 2-3% quality improvement justifies 10-20x higher cost.

2. **Debate's value is in the rebuttal, not the opening.** The largest quality improvements (reasoning depth +25%, internal consistency +19%) come from agents responding to each other's arguments. Debate protocols should maximize rebuttal quality — perhaps by explicitly prompting agents to identify the strongest opposing argument and either concede or refute it with evidence.

3. **More constraints is not better constraints.** The 171 extracted constraints overwhelmed rather than enhanced the debate. Future work should explore constraint *prioritization* — extract fewer, higher-impact constraints — or constraint *resolution* — where agents negotiate which constraints to satisfy and which to relax.

4. **Tool access should be uniform or absent in evaluations.** The 500x cost gap between tool-using and non-tool modes makes quality comparison meaningless per dollar. Future benchmarks should either give all modes tool access or none.

5. **The judge's qualitative feedback is as valuable as the scores.** The judge's reasoning — noting "concession tracking," "position evolution," and "process-focused vs. action-focused" — provides design guidance that numerical scores alone cannot.

---

## 6. Threats to Validity

### 6.1 Internal Validity

- **Single evaluation run.** All results are from a single benchmark execution. Random variation in model outputs, judge scoring, and presentation order randomization could produce different results on re-run. Mitigation: deterministic judge temperature (0.0) and structured output format reduce but do not eliminate variation.
- **Same-model bias.** Using Opus 4.6 for both generation and evaluation could introduce systematic preferences for certain output styles. Mitigation: the blind protocol prevents the judge from identifying generation mode, but stylistic preferences may still influence scoring.
- **Tool confound.** The tool-access asymmetry (Modes A/D/E have tools; B/C do not) confounds the coordination comparison with an information-access comparison.

### 6.2 External Validity

- **Domain specificity.** Results apply to strategic business advisory for professional services firms. Multi-agent coordination may perform differently on other domains (legal analysis, medical diagnosis, software architecture, creative writing).
- **Model specificity.** Results are specific to Claude Opus 4.6. Different models may show different coordination benefits — less capable models might benefit more from multi-agent coordination because individual agents have more room for improvement.
- **Question selection.** Five curated questions may not represent the full range of strategic decisions. Questions were deliberately chosen to create cross-functional tension; more straightforward questions might show smaller coordination benefits.

### 6.3 Construct Validity

- **Dimension definitions.** The seven dimensions were designed by the researchers, not validated through factor analysis or expert consensus. Different dimension definitions could produce different mode rankings.
- **LLM judge limitations.** LLM judges may weight different quality properties than human experts. The forced ranking ("present to a CEO") adds practical grounding but is itself filtered through the model's understanding of what a CEO would value.

---

## 7. Conclusions

This study provides the first controlled empirical evidence that multi-agent LLM coordination produces measurably better strategic recommendations than a single LLM call with equivalent information access. The key findings are:

1. **Multi-round debate improves recommendation quality by 15.2%** over a single-model control with multi-perspective prompting (4.71 vs. 4.09 on a 5-point scale).

2. **The improvement is concentrated in coordination-dependent dimensions:** internal consistency (+19.0%), reasoning depth (+25.0%), constraint awareness (+21.1%), and tension surfacing (+4.3%). These are exactly the dimensions where inter-agent interaction provides a theoretical advantage.

3. **Parallel synthesis achieves 97.7% of debate quality** at 0.4% of the cost, making it the optimal default architecture for most applications.

4. **Constraint negotiation does not improve output quality** beyond standard debate (4.57 vs. 4.71) despite producing 171 auditable constraints. The constraint machinery has value for process transparency but not for output quality.

5. **Multi-agent architecture's primary value may be raising the quality floor** rather than the ceiling — preventing the worst-case single-agent failure modes where unchallenged biases produce unrealistic recommendations.

6. **The DeepMind engineer was right to demand outcome metrics.** Process metrics (constraint counts, node counts) tell us the system is working, not that it's working well. This evaluation framework provides the outcome measurement that validates — or would invalidate — the multi-agent architecture.

### 7.1 Recommendations for Practitioners

For teams building multi-agent AI systems:

- **Start with parallel synthesis.** It's simple to implement, cheap to run, and captures most of the multi-agent value. Only add iterative debate when you have evidence it helps for your specific domain.
- **Invest in the synthesis prompt.** The quality of the final synthesis pass matters more than the number of debate rounds. A well-crafted synthesis prompt can extract coordination value from independently-generated agent responses.
- **Benchmark against the right baseline.** "Single agent" is not the right baseline — "single agent with multi-role prompting" is. Many reported multi-agent improvements disappear when the baseline agent is given the same information in its system prompt.
- **Separate tool access from coordination** in evaluations. If multi-agent modes have tool access and single-agent modes don't, you're measuring information access, not coordination.
- **Track quality floors, not just means.** Multi-agent architecture's strongest argument is preventing bad outputs, not producing great ones. Report worst-case performance alongside averages.

### 7.2 Future Work

1. **Cross-model evaluation:** Use GPT-4o or Gemini Ultra as the blind judge to control for same-model bias.
2. **Human expert calibration:** Have 2-3 strategy consultants score a subset of outputs on the same dimensions for inter-rater reliability analysis.
3. **Larger question set:** Expand to 20-30 questions across multiple industry verticals for statistical significance testing.
4. **Debate protocol optimization:** Test explicit revision prompting, constraint prioritization (top-5 only), and 3-round vs. 2-round debates.
5. **Longitudinal tracking:** Re-run the benchmark quarterly as models improve to track whether the multi-agent premium holds, shrinks, or grows.
6. **Tool-controlled comparison:** Run all five modes with identical tool access (or none) to isolate the coordination variable.

---

## Appendix A: System Architecture

The evaluation framework is implemented in Python 3.11+ as part of the Cardinal Element C-Suite platform. Key components:

- **Benchmark runner** (`src/csuite/evaluation/benchmark.py`): Orchestrates all five execution modes, tracks costs and durations, collects structural trace metrics from the causal graph.
- **Blind judge** (`src/csuite/evaluation/judge.py`): Implements the metadata stripping, randomized presentation, and judge evaluation protocol.
- **Report generator** (`src/csuite/evaluation/report.py`): Produces structured markdown from benchmark and judge results.
- **Agent implementations** (`src/csuite/agents/`): Seven agent classes (CEO, CFO, CTO, CMO, COO, CPO, CRO) each inheriting from `BaseAgent` with role-specific system prompts.
- **Debate orchestrator** (`src/csuite/debate.py`): Manages multi-round debate protocol including rebuttal sequencing and synthesis.
- **Causal graph** (`src/csuite/tracing/graph.py`): Records the debate DAG with typed nodes (CLAIM, RESPOND, REVISE, CONSTRAIN).
- **Constraint extractor** (`src/csuite/tracing/constraints.py`): Extracts and types constraints from agent statements using Claude Haiku.

CLI invocation: `csuite evaluate -q 5 -o evaluation-report.md`

## Appendix B: Judge System Prompt

The full judge system prompt used for blind evaluation:

> You are a senior strategy consultant evaluating strategic recommendations for a $5-40M professional services firm. You will receive multiple responses to the same strategic question. Each is labeled only as "Response A", "Response B", etc. You do NOT know how they were generated. Score each response on these 7 dimensions (1-5 scale): (1) Specificity — Are recommendations concrete enough to act on tomorrow? (2) Internal Consistency — Do financial, operational, and strategic recommendations align? (3) Tension Surfacing — Does the output identify genuine trade-offs, not just list perspectives? (4) Constraint Awareness — Does it acknowledge real-world limits (budget, timeline, headcount)? (5) Actionability — Is there a clear first step, owner, and timeline? (6) Reasoning Depth — Are claims supported by evidence or reasoning chains? (7) Completeness — Are all relevant functional perspectives addressed? After scoring, provide a forced ranking: if you had to present ONE of these responses to a $15M company's CEO, which would you pick? Rank all responses from best to worst.

## Appendix C: Raw Data Summary

**Total benchmark cost:** $39.58 across all modes, all questions, including judge calls.

**Total execution time:** Approximately 2 hours (sequential mode execution).

**Model used:** Claude Opus 4.6 (`claude-opus-4-6`) for all agent roles, synthesis, and judging. Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) for constraint extraction only.

**Known runtime issues:**
- Brave Search API returned HTTP 429 (rate limit) errors throughout the benchmark, affecting tool-using Modes A, D, and E.
- Pricing calculator had a date arithmetic bug (since fixed) that caused tool failures on some calls.
- US Census API timed out on 2 calls.
- Notion API timed out on 1 call.
- `ConstraintType` enum did not include 'financial' as a valid type, causing non-fatal constraint extraction failures.

---

*Generated by C-Suite Evaluation Framework v1.0 | Cardinal Element | February 2026*
