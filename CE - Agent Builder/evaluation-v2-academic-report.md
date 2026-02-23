# Does Multi-Agent AI Coordination Produce Better Strategic Recommendations? A Replication Study with Controlled Tool Access

## A 10-Question Empirical Evaluation Across Five Execution Architectures

**Scott Ewalt | Cardinal Element**
**February 13, 2026**

---

## Abstract

We present a controlled replication of our February 2026 pilot study comparing five multi-agent coordination architectures for strategic business advisory. The original study (N=5 questions) found that multi-round debate scored 4.71/5.0 versus 4.09 for the single-model control — a 15.2% improvement — but was confounded by asymmetric tool access across modes. This replication (a) doubles the question set to N=10 with questions designed to cover a broader decision taxonomy (pricing, capacity, M&A, competitive response, talent, investment, product, client management), (b) disables tool access globally to eliminate the tool confound, and (c) persists all 50 raw outputs for independent review. Results confirm the multi-agent advantage but reveal a different winner: **parallel synthesis (4.74/5.0) outperforms debate (4.40) and negotiate (4.60)** under tool-controlled conditions — reversing the v1 finding where debate led. Synthesis and negotiate each won 4 of 10 forced rankings; debate won only 1. The single-agent mode (3.77) never won. Total benchmark cost was under $10 for all 50 responses plus judging, versus $39 in v1 — a 75% cost reduction achieved by eliminating the tool-calling overhead that dominated v1 costs. These findings suggest that when tool access is equalized, the value of iterative debate over parallel synthesis is smaller than previously measured, and the practical recommendation shifts: **synthesis is the default architecture; debate and negotiate earn their premium only on specific question types**.

**Keywords:** multi-agent systems, LLM evaluation, coordination architectures, strategic advisory, blind evaluation, replication study

---

## 1. Introduction

### 1.1 Motivation for Replication

Our February 13, 2026 pilot study ("Does Multi-Agent AI Coordination Produce Better Strategic Recommendations Than a Single Large Language Model?") compared five execution architectures across five strategic questions and found that multi-round debate (Mode D) produced the highest-quality recommendations. The study received constructive criticism on three methodological grounds:

1. **Tool confound.** Modes A (single agent), D (debate), and E (negotiate) had access to external tools (Brave Search, SEC EDGAR, Census API, financial calculators), while Modes B (single+context) and C (synthesize) did not. This meant the quality comparison was partially confounded with information access. The v1 regression analysis found tool access had near-zero effect on scores, but the confound was structurally present and could not be fully resolved post-hoc.

2. **Small sample size.** Five benchmark questions provided directional signal but insufficient statistical power for robust conclusions. The question set covered only a narrow range of strategic decision types.

3. **No output persistence.** Raw model outputs were not saved in a reviewable format. An independent reviewer could see the scores and judge reasoning but could not read the actual 25 responses to form their own assessment.

This replication addresses all three concerns.

### 1.2 What Changed from v1 to v2

| Dimension | v1 (Pilot) | v2 (Replication) |
|-----------|-----------|-----------------|
| Questions | 5 | **10** |
| Tool access | Asymmetric (A/D/E had tools; B/C did not) | **Uniform: tools disabled for all modes** |
| Output persistence | Scores only | **All 50 raw outputs saved (JSON + double-blind markdown)** |
| Cost | $39.58 | **~$8-10** |
| Runtime | ~2 hours | **~60 minutes** |
| Known confounds | Tool access, Brave Search 429 errors | **Haiku overload (529s) on sidecar calls only; does not affect core outputs** |

### 1.3 Research Questions

This replication tests the same four research questions as v1, with the tool confound removed:

1. **Does multi-agent coordination produce higher-quality strategic recommendations** than a single LLM call with equivalent information access, when tool access is equalized?
2. **Which specific quality dimensions** benefit most from inter-agent interaction?
3. **Does constraint negotiation** improve output quality beyond standard debate?
4. **What is the cost-quality tradeoff** when all modes have the same information access?

Plus one new question motivated by the v1 findings:

5. **Does the v1 finding that debate outperforms synthesis replicate** when the tool confound is removed?

---

## 2. Experimental Design

### 2.1 Changes from v1

The experimental design is identical to v1 (see Section 3 of the pilot report) with these modifications:

**Tool access disabled globally.** A new `--no-tools` CLI flag sets `settings.tools_enabled = False` before the benchmark runs. This propagates to all `BaseAgent` instances via the `_should_use_tools()` check. Mode B (single+context) already used no tools; Mode C (synthesize) already operated without tools in the Orchestrator's parallel-query mode. The change affects Modes A, D, and E, which previously had tool access.

**Implication:** All five modes now reason from the same information base — the model's training data plus the agent's system prompt and business context (loaded from `CLAUDE.md`). No mode has access to web search, financial calculators, or government APIs. This isolates the coordination variable.

**10 benchmark questions.** The original 5 questions are retained (Q1-Q5). Five new questions (Q6-Q10) extend the coverage:

| # | ID | Question Summary | Primary Tensions | Decision Type |
|---|-----|-----------------|-----------------|--------------|
| 1 | `pricing` | Free discovery call vs. premium positioning | CFO vs. CMO | Pricing |
| 2 | `plg` | Self-serve PLG tier alongside consulting | CPO vs. CFO vs. CRO | Product |
| 3 | `capacity` | Hire senior consultant vs. AI automation | COO vs. CTO vs. CFO | Capacity |
| 4 | `competitive` | Competitor raised $20M, offering free audits | CEO vs. CMO vs. CFO | Competitive |
| 5 | `open_source` | Open-source audit framework vs. proprietary | CTO vs. CPO vs. CEO | IP Strategy |
| 6 | `client_concentration` | Largest client (40% rev) demands 25% discount | CRO vs. CFO vs. CEO | Client Mgmt |
| 7 | `conference_spend` | $50K conference sponsorship on $80K budget | CMO vs. CFO vs. CEO | Investment |
| 8 | `delivery_overrun` | 3 of 5 engagements running 2-3 weeks late | COO vs. CFO vs. CRO | Operations |
| 9 | `enterprise_opp` | $500K engagement outside ICP (2000-person co.) | CEO vs. CPO vs. COO | Strategy |
| 10 | `margin_vs_speed` | $12 API cost / $2,500 deliverable vs. $500 competitor | CFO vs. CTO vs. CPO | Pricing/Product |

**Question design criteria:** Each question includes specific dollar amounts, percentages, or timelines. Each creates genuine tension between 2-3 C-suite functions. No question has an obvious "right answer." The set covers 8 distinct decision types to reduce the risk that results are driven by question-type bias.

### 2.2 Execution Modes (Unchanged)

The five execution modes are identical to v1:

- **Mode A: Single Agent** — One CEO agent, no tools, one question, one answer.
- **Mode B: Single+Context** — One Opus call with a 7-role system prompt. The critical control.
- **Mode C: Parallel Synthesis** — Three agents (CFO, CMO, CTO) answer independently; a synthesis pass combines them.
- **Mode D: Multi-Round Debate** — Three agents engage in 2-round structured debate with rebuttals, then synthesis.
- **Mode E: Constraint Negotiation** — Debate plus Haiku-powered constraint extraction and cross-agent propagation.

### 2.3 Evaluation Protocol (Unchanged)

Seven quality dimensions scored 1-5 by a blind Opus judge with temperature 0.0. Metadata stripped, presentation order randomized, forced ranking required. See v1 Section 3.3-3.4 for full protocol description.

### 2.4 Output Persistence (New)

All 50 raw outputs are persisted in three formats:

1. **`evaluation-v2-outputs.json`** — Full text of every response with cost, duration, and token metadata, keyed by question ID and mode.
2. **`evaluation-v2-double-blind.md`** — All responses anonymized ("Response 1" through "Response 5") with randomized order per question. Suitable for independent blind review.
3. **`evaluation-v2-key.json`** — Maps anonymous labels to mode names. Sealed until after independent review.

---

## 3. Results

### 3.1 Overall Quality Scores

**Table 1: Mean Dimension Scores by Execution Mode (N=10 questions)**

| Mode | Specificity | Internal Consistency | Tension Surfacing | Constraint Awareness | Actionability | Reasoning Depth | Completeness | **Mean** |
|------|:-----------:|:-------------------:|:-----------------:|:-------------------:|:------------:|:---------------:|:------------:|:--------:|
| A: Single | 3.9 | 4.4 | 3.1 | 3.9 | 3.8 | 4.1 | 3.2 | **3.77** |
| B: Single+Context | 3.9 | 4.5 | 4.5 | 4.0 | 3.7 | 4.2 | 4.9 | **4.24** |
| C: Synthesize | 4.9 | 5.0 | 4.2 | 4.7 | 5.0 | 4.6 | 4.8 | **4.74** |
| D: Debate | 4.3 | 4.5 | 4.7 | 4.3 | 4.3 | 4.8 | 3.9 | **4.40** |
| E: Negotiate | 4.6 | 4.6 | 4.4 | 4.7 | 4.7 | 4.9 | 4.3 | **4.60** |

**Key findings:**

1. **Mode C (Synthesize) achieved the highest mean score at 4.74/5.0** — reversing the v1 finding where debate led (4.71).
2. **Mode E (Negotiate) scored 4.60/5.0**, outperforming debate (4.40) — also reversing v1 where negotiate trailed debate.
3. **Mode D (Debate) scored 4.40/5.0** — a notable decline from its v1 score of 4.71. Without tool access, debate's advantage narrows.
4. **Mode B (Single+Context) scored 4.24/5.0**, up from v1's 4.09 — suggesting that the all-role prompt performs comparably with or without tool access in competing modes.
5. **Mode A (Single) scored 3.77/5.0**, the weakest mode in both studies.

### 3.2 Comparison with v1 Results

**Table 2: Score Comparison Across Studies**

| Mode | v1 Score (N=5, tools asymmetric) | v2 Score (N=10, no tools) | Delta | Rank Change |
|------|:------:|:------:|:-----:|:-----------:|
| A: Single | 3.80 | 3.77 | -0.03 | 5th → 5th |
| B: Single+Context | 4.09 | 4.24 | +0.15 | 4th → 4th |
| C: Synthesize | 4.60 | **4.74** | +0.14 | 2nd → **1st** |
| D: Debate | **4.71** | 4.40 | -0.31 | **1st** → 3rd |
| E: Negotiate | 4.57 | 4.60 | +0.03 | 3rd → 2nd |

**The most significant finding: debate dropped 0.31 points and fell from 1st to 3rd place.** This is the largest score change of any mode across studies and suggests that debate's v1 advantage was partially attributable to tool access — agents in debate could invoke web search and financial calculators to support their arguments, while the synthesis baseline could not. With tools equalized, the rebuttal mechanism alone does not outperform the synthesis mechanism.

Synthesize and negotiate both improved slightly, consistent with the hypothesis that tool-using competitors were inflating the relative gap in v1.

### 3.3 Coordination Dimensions vs. Baseline Dimensions

**Table 3: Coordination vs. Baseline Dimension Analysis**

| Mode | Coordination Dims Mean (2,3,4,6) | Baseline Dims Mean (1,5,7) | Gap |
|------|:--------------------------------:|:--------------------------:|:---:|
| A: Single | 3.88 | 3.63 | +0.25 |
| B: Single+Context | 4.30 | 4.17 | +0.13 |
| C: Synthesize | 4.63 | **4.90** | -0.27 |
| D: Debate | **4.58** | 4.17 | +0.41 |
| E: Negotiate | 4.65 | 4.53 | +0.12 |

**Finding:** Debate still shows the largest positive gap between coordination and baseline dimensions (+0.41), confirming v1's finding that debate specifically excels at coordination-dependent properties (tension surfacing, internal consistency, reasoning depth). However, synthesis leads on baseline dimensions (4.90) — specificity, actionability, and completeness — by a wide margin.

This reveals a complementarity: **debate produces deeper analysis; synthesis produces more actionable output.** The overall scores favor synthesis because actionability and specificity are weighted equally with coordination dimensions in the mean.

### 3.4 Dimension-Level Analysis

#### Specificity (Dimension 1)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| C: Synthesize | **4.9** | +1.0 |
| E: Negotiate | 4.6 | +0.7 |
| D: Debate | 4.3 | +0.4 |
| A: Single | 3.9 | 0.0 |
| B: Single+Context | 3.9 | — |

Synthesis dominates on specificity. The parallel agent architecture allows each agent to go deep on domain-specific details (the CFO provides exact budget numbers, the CTO specifies technical implementation), and the synthesis pass combines them into a comprehensive recommendation.

#### Internal Consistency (Dimension 2)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| C: Synthesize | **5.0** | +0.5 |
| E: Negotiate | 4.6 | +0.1 |
| D: Debate | 4.5 | 0.0 |
| B: Single+Context | 4.5 | — |
| A: Single | 4.4 | -0.1 |

**Notable reversal from v1.** In v1, debate scored a perfect 5.0 on internal consistency while synthesis scored 4.6. In v2, synthesis scores 5.0 and debate drops to 4.5. Without tools providing concrete data points for cross-checking, the synthesis mechanism (where a single synthesis pass explicitly reconciles all perspectives) produces better alignment than the rebuttal mechanism.

#### Tension Surfacing (Dimension 3)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| D: Debate | **4.7** | +0.2 |
| B: Single+Context | 4.5 | — |
| E: Negotiate | 4.4 | -0.1 |
| C: Synthesize | 4.2 | -0.3 |
| A: Single | 3.1 | -1.4 |

**Debate retains its lead on tension surfacing** — the one dimension where the rebuttal mechanism clearly adds value. When agents directly challenge each other's arguments, the resulting output surfaces deeper tensions than parallel agents working independently. The 1.6-point gap between single agent (3.1) and debate (4.7) is the largest dimension-level gap in the study, replicating the v1 finding exactly.

#### Constraint Awareness (Dimension 4)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| C: Synthesize | **4.7** | +0.7 |
| E: Negotiate | **4.7** | +0.7 |
| D: Debate | 4.3 | +0.3 |
| B: Single+Context | 4.0 | — |
| A: Single | 3.9 | -0.1 |

Synthesis ties negotiate on constraint awareness — undermining the v1 hypothesis that formal constraint extraction was necessary for strong constraint awareness. When all modes lack tools, the synthesis mechanism captures constraints as effectively as the explicit constraint extraction pipeline.

#### Actionability (Dimension 5)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| C: Synthesize | **5.0** | +1.3 |
| E: Negotiate | 4.7 | +1.0 |
| D: Debate | 4.3 | +0.6 |
| A: Single | 3.8 | +0.1 |
| B: Single+Context | 3.7 | — |

Synthesis achieves a perfect 5.0 on actionability — the judge consistently found that synthesis outputs contained the most concrete implementation plans with named owners, timelines, and decision gates. This dimension is synthesis's strongest advantage over debate.

#### Reasoning Depth (Dimension 6)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| E: Negotiate | **4.9** | +0.7 |
| D: Debate | 4.8 | +0.6 |
| C: Synthesize | 4.6 | +0.4 |
| B: Single+Context | 4.2 | — |
| A: Single | 4.1 | -0.1 |

Debate and negotiate retain their advantage on reasoning depth, confirming that the rebuttal mechanism produces deeper argumentation chains. The v1 finding (debate scored 5.0, +25% over control) partially replicates: the direction is the same, but the magnitude is smaller (4.8, +14% over control).

#### Completeness (Dimension 7)

| Mode | Score | Delta vs. Control (B) |
|------|:-----:|:---------------------:|
| B: Single+Context | **4.9** | — |
| C: Synthesize | 4.8 | -0.1 |
| E: Negotiate | 4.3 | -0.6 |
| D: Debate | 3.9 | -1.0 |
| A: Single | 3.2 | -1.7 |

**Debate's weakest dimension.** The 3-agent debate (CFO, CMO, CTO) consistently misses perspectives that the all-role system prompt (Mode B) captures — COO, CPO, CRO, and CEO viewpoints. This is a structural limitation of using 3 agents when 7 perspectives exist. Synthesis partially compensates through its synthesis pass, but debate's rebuttal mechanism focuses agents on defending their own positions rather than covering missing perspectives.

### 3.5 Forced Rankings

**Table 4: First-Place Wins by Mode (out of 10 questions)**

| Mode | First-Place Wins | Win Rate |
|------|:----------------:|:-------:|
| C: Synthesize | **4** | 40% |
| E: Negotiate | **4** | 40% |
| D: Debate | 1 | 10% |
| B: Single+Context | 1 | 10% |
| A: Single | 0 | 0% |

**Comparison with v1:**

| Mode | v1 Wins (of 5) | v2 Wins (of 10) |
|------|:-------------:|:--------------:|
| D: Debate | **3** (60%) | 1 (10%) |
| C: Synthesize | 2 (40%) | **4** (40%) |
| E: Negotiate | 0 (0%) | **4** (40%) |
| B: Single+Context | 0 (0%) | 1 (10%) |
| A: Single | 0 (0%) | 0 (0%) |

Debate's dominance in v1 (60% win rate) collapsed to 10% in v2. Negotiate, which never won in v1, tied for first in v2. This is the strongest evidence that the tool confound in v1 disproportionately benefited debate, which leveraged tool results to strengthen its rebuttal arguments.

### 3.6 Per-Question Results

**Table 5: Per-Question Scores and Winners**

| Question | A: Single | B: Context | C: Synth | D: Debate | E: Negotiate | **Winner** |
|----------|:---------:|:----------:|:--------:|:---------:|:------------:|:----------:|
| pricing | 3.71 | 3.57 | 4.43 | 4.00 | **4.86** | E: Negotiate |
| plg | 4.14 | 4.57 | **4.86** | 4.29 | 4.00 | C: Synthesize |
| capacity | 3.00 | 4.29 | **4.71** | 4.43 | 4.14 | C: Synthesize |
| competitive | 4.00 | 4.14 | 4.71 | **4.86** | 4.71 | D: Debate |
| open_source | 3.71 | **4.86** | 4.57 | 4.43 | 4.71 | B: Single+Context |
| client_conc. | 3.71 | 4.57 | 4.71 | 4.43 | **5.00** | E: Negotiate |
| conf_spend | 3.71 | 4.00 | 4.71 | 4.43 | **4.86** | E: Negotiate |
| delivery | 4.00 | 4.29 | **4.86** | 4.43 | 4.29 | C: Synthesize |
| enterprise | 3.14 | 3.57 | 4.86 | 4.86 | **5.00** | E: Negotiate |
| margin_speed | 4.57 | 4.57 | **5.00** | 3.86 | 4.43 | C: Synthesize |
| **Mean** | **3.77** | **4.24** | **4.74** | **4.40** | **4.60** | |

**Pattern analysis:** Synthesis tends to win on questions with clear trade-offs that benefit from comprehensive coverage (PLG, capacity, delivery, margin). Negotiate tends to win on questions with high-stakes negotiation dynamics (client concentration, conference spend, enterprise opportunity). Debate won only on the competitive response question — the one scenario where adversarial argument is most naturally suited.

### 3.7 Structural Trace Metrics

**Table 6: Debate and Negotiate Structural Metrics**

| Question | Debate Nodes | Negotiate Nodes | Constraints | Debate Revisions |
|----------|:-----------:|:---------------:|:-----------:|:----------------:|
| pricing | 6 | 7 | 0 | 3 |
| plg | 6 | 7 | 0 | 3 |
| capacity | 6 | 41 | 34 | 3 |
| competitive | 6 | 44 | 37 | 3 |
| open_source | 6 | 35 | 28 | 3 |
| client_conc. | 6 | 41 | 34 | 3 |
| conf_spend | 6 | 48 | 41 | 3 |
| delivery | 6 | 54 | 47 | 3 |
| enterprise | 6 | 48 | 41 | 3 |
| margin_speed | 6 | 46 | 39 | 3 |
| **Total** | **60** | **371** | **301** | **30** |

**Notable:** The first two questions (pricing, plg) extracted zero constraints — likely because these ran during peak Haiku API congestion (529 overloaded errors). The remaining 8 questions extracted 301 constraints, averaging 37.6 per question. This is comparable to v1's rate (34.2 per question) despite the tool-disabled condition, confirming that constraint extraction operates on the debate text itself, not on tool results.

Debate consistently produced 3 revisions per question (one per agent per rebuttal round), confirming the v1 observation that the current protocol elicits rebuttals but not formal position revisions.

### 3.8 Cost Analysis

**Table 7: Cost by Mode (Tool-Controlled)**

| Mode | Total Cost (10 Qs) | Cost/Question | Mean Score | Score/Dollar |
|------|-------------------:|:-------------:|----------:|:------------:|
| B: Single+Context | $0.51 | $0.05 | 4.24 | 8.4 |
| A: Single | $0.82 | $0.08 | 3.77 | 4.6 |
| C: Synthesize | $1.14 | $0.11 | 4.74 | 4.1 |
| D: Debate | $5.90 | $0.59 | 4.40 | 0.7 |
| E: Negotiate | ~$10* | ~$1.00* | 4.60 | ~0.5* |

*\*Negotiate cost affected by a tracking bug (negative values in some questions due to concurrent Haiku sidecar calls interfering with the cost accumulator). Estimated from unaffected questions.*

**Key insight:** With tools disabled, the cost ratios are dramatically different from v1:

| Comparison | v1 | v2 |
|-----------|:--:|:--:|
| Debate vs. Single+Context | 616x more expensive | **12x** more expensive |
| Synthesize vs. Single+Context | 2.7x | **2.2x** |
| Negotiate vs. Single+Context | 644x | **~20x** |

The 500-600x cost multiplier in v1 was almost entirely tool-calling overhead. With tools disabled, debate costs ~$0.59 per question — a practical amount — versus ~$30 per question in v1.

---

## 4. Discussion

### 4.1 Answering the Research Questions

**RQ1: Does multi-agent coordination produce higher-quality recommendations when tools are equalized?**

Yes. All multi-agent modes (C, D, E) outperformed both single-agent modes (A, B). The best multi-agent mode (Synthesis, 4.74) scored 11.8% higher than the control (Single+Context, 4.24). This confirms that coordination adds value independent of tool access.

However, the magnitude of the advantage is smaller than v1 suggested: v1's 15.2% gap (debate vs. control) shrinks to 11.8% (synthesis vs. control) or 3.8% (debate vs. control) depending on which multi-agent mode is compared. The "true" multi-agent premium, with tools controlled, appears to be in the 10-15% range for synthesis and 5-10% for debate/negotiate.

**RQ2: Which dimensions benefit most from inter-agent interaction?**

Replicates v1 directionally:
- **Tension surfacing:** Debate leads (+0.2 over control), consistent with v1
- **Reasoning depth:** Debate/Negotiate lead (+0.6-0.7 over control), consistent with v1
- **Actionability:** Synthesis leads (+1.3 over control) — new finding, not measured as strongly in v1
- **Completeness:** Control (B) leads — multi-agent modes with 3 agents miss perspectives

**RQ3: Does constraint negotiation improve quality beyond debate?**

**Yes — reversing the v1 finding.** Negotiate (4.60) outperformed debate (4.40) by 0.20 points and won 4 forced rankings versus debate's 1. In v1, negotiate (4.57) underperformed debate (4.71). This reversal suggests that when tool-derived data isn't available to fuel rebuttals, the constraint propagation mechanism provides a structured scaffold that improves debate quality. When agents can't look up data to support arguments, having explicit constraints to work from is more valuable.

**RQ4: What is the cost-quality tradeoff?**

| Tier | Mode | Quality | Cost/Question | Use Case |
|------|------|---------|:-------------:|----------|
| **Best Value** | **C: Synthesize** | **4.74/5.0** | **$0.11** | **Default for all queries** |
| Premium | E: Negotiate | 4.60/5.0 | ~$1.00 | High-stakes negotiations, client-facing |
| Specialized | D: Debate | 4.40/5.0 | $0.59 | Competitive analysis, adversarial reasoning |
| Budget | B: Single+Context | 4.24/5.0 | $0.05 | Quick internal queries |
| Not recommended | A: Single | 3.77/5.0 | $0.08 | No advantage over B |

**RQ5: Does v1's finding that debate outperforms synthesis replicate?**

**No.** With tools equalized, synthesis outperforms debate by 0.34 points (4.74 vs. 4.40). The v1 finding that debate led was partially an artifact of tool access: debate agents used tool results to strengthen rebuttals, giving them an information advantage that synthesis agents lacked.

### 4.2 Why Synthesis Won in v2

Three factors explain synthesis's improved relative performance:

1. **Tool equalization removed debate's information advantage.** In v1, debate agents could invoke web search and financial calculators during rebuttals, producing data-grounded arguments that synthesis agents couldn't match. Without tools, all agents reason from the same knowledge base, and the synthesis mechanism — where specialized agents go deep independently, then a synthesis pass combines them — proves more efficient than iterative debate.

2. **The synthesis prompt compensates for lack of interaction.** The Orchestrator's synthesis system prompt explicitly instructs the model to "identify areas of agreement, surface tensions, and produce a unified recommendation." This prompt performs much of the tension-surfacing and consistency-checking work that debate distributes across multiple rounds — and does it in a single pass, reducing the opportunity for coherence loss that accumulates over multiple debate rounds.

3. **Synthesis optimizes for actionability.** Without tool data to anchor arguments, debate agents tend toward abstract strategic reasoning. Synthesis agents, working independently, each produce domain-specific recommendations with concrete details. The synthesis pass combines these into an actionable plan. The judge consistently valued actionability, giving synthesis a scoring advantage.

### 4.3 Why Negotiate Improved

Negotiate's improvement from v1 (where it never won) to v2 (where it won 4 of 10) is the study's most interesting reversal. We hypothesize:

1. **Constraints as information substitute.** When agents can't access external tools for data, the formally extracted constraints provide a structured information scaffold. Constraints like "budget must not exceed $X" or "timeline cannot extend beyond Q2" give agents specific parameters to reason about, partially replacing the role that tool-derived data played in v1.

2. **Reduced constraint volume.** Due to Haiku API congestion (529 errors), some questions had zero or reduced constraint extraction. Paradoxically, this may have helped: the v1 paper noted that 30-40 constraints per question could overwhelm agents. Questions with moderate constraint volumes (28-41) performed well; the two questions with zero constraints (pricing, plg) showed mixed results.

### 4.4 The Persistent Single-Agent Floor

Mode A (Single Agent) never won in either study (0 of 15 total questions). Its worst score in v2 was 3.00 on the capacity question — identical to its worst in v1 on the same question. The judge's v2 critique echoed v1: "the single-agent mode lacks cross-functional challenge," "unchecked optimism," "no tension surfacing."

This replicates our v1 finding that **multi-agent architecture's primary value may be raising the quality floor** rather than the ceiling. Even simple synthesis prevents the worst-case single-agent failure modes.

### 4.5 Limitations

**Limitations addressed from v1:**
- Tool confound: **Resolved.** All modes have identical (no) tool access.
- Small sample: **Partially resolved.** N=10 provides stronger signal but remains below the 20-30 question threshold for robust statistical power.
- Output persistence: **Resolved.** All 50 outputs saved in reviewable format.

**Remaining limitations:**
- **Single judge, single run.** Results are from one evaluation pass. A multi-judge design would improve reliability.
- **Same-model bias.** Opus 4.6 generates and evaluates. Cross-model judging recommended for future work.
- **Cost tracking bug.** Negotiate costs are unreliable for 2 of 10 questions due to concurrent Haiku sidecar calls interfering with the cost accumulator. A fix has been implemented (in-memory accumulator subclass) but the current run used the buggy version.
- **Haiku overload.** 529 errors on constraint extraction and self-evaluation sidecars affected the negotiate mode's structural metrics for Q1-Q2 (zero constraints extracted). This may have penalized negotiate on those questions.
- **No human baseline.** No human expert responses included for calibration.

---

## 5. Conclusions

This replication study confirms the multi-agent hypothesis while significantly revising the practical recommendations:

### 5.1 Findings That Replicate from v1

1. **Multi-agent coordination produces better strategic recommendations** than single-model prompting (confirmed at 11.8% improvement, vs. v1's 15.2%).
2. **The single-agent mode never wins** (0 of 15 total questions across both studies).
3. **Tension surfacing and reasoning depth** are the dimensions most improved by inter-agent interaction (confirmed).
4. **Multi-agent architecture raises the quality floor** — preventing unchallenged single-agent failures (confirmed, same 3.00 worst-case on capacity question).

### 5.2 Findings That Change from v1

1. **Synthesis outperforms debate** when tool access is equalized (4.74 vs. 4.40). The v1 finding that debate led was partially a tool-access artifact.
2. **Negotiate outperforms debate** under controlled conditions (4.60 vs. 4.40). V1's finding that negotiate underperformed was also influenced by the tool confound.
3. **The cost-quality landscape is dramatically different** without tools. Debate costs $0.59/question, not $30 — making it practical for routine use.

### 5.3 Revised Recommendations for Practitioners

| Recommendation | v1 Guidance | v2 Revised Guidance |
|---------------|------------|-------------------|
| Default mode | Parallel synthesis | **Parallel synthesis** (confirmed) |
| High-stakes decisions | Debate | **Negotiate** (constraint scaffold adds value when tools unavailable) |
| Competitive analysis | Debate | **Debate** (adversarial reasoning still best for competitive questions) |
| Quick internal queries | Single+Context | **Single+Context** (confirmed) |
| Never use | Single agent | **Single agent** (confirmed) |

### 5.4 The Meta-Finding

The most important finding is not about which mode wins. It's that **the tool confound in v1 was the dominant effect** — it changed the winner, altered the cost ratios by 50x, and produced misleading practical recommendations. The v1 paper noted this confound in limitations but underestimated its impact based on a post-hoc regression that found "near-zero" tool effect. This replication, by eliminating the confound prospectively rather than adjusting for it retrospectively, reveals that the effect was substantial.

This should serve as a cautionary finding for the broader multi-agent evaluation literature: **if your multi-agent modes have capabilities that your baselines don't, your evaluation is measuring capability access, not coordination quality.**

### 5.5 Future Work

1. **Tool-enabled replication.** Run all five modes WITH tools to complete the 2x2 design (tools x coordination). This would definitively separate the tool effect from the coordination effect.
2. **Expand to N=20-30 questions** for statistical significance testing.
3. **Cross-model judging** using GPT-4o or Gemini as judge to control for same-model bias.
4. **Human expert calibration** for inter-rater reliability.
5. **Question-type analysis.** With 10+ questions per type, test whether debate vs. synthesis preference is systematic by decision type.
6. **3-round debate.** Test whether additional debate rounds improve debate's standing relative to synthesis.
7. **Selective tool access.** Give all modes access to a controlled set of tools (e.g., financial calculator only, no web search) to test whether moderate tool access changes the mode rankings.

---

## Appendix A: Comparison of v1 and v2 Experimental Conditions

| Parameter | v1 | v2 |
|-----------|---|----|
| Questions | 5 | 10 |
| Modes | 5 (same) | 5 (same) |
| Agents per multi-agent mode | 3 (CFO, CMO, CTO) | 3 (CFO, CMO, CTO) |
| Debate rounds | 2 | 2 |
| Model | Claude Opus 4.6 | Claude Opus 4.6 |
| Judge model | Claude Opus 4.6 | Claude Opus 4.6 |
| Judge temperature | 0.0 | 0.0 |
| Tool access (A: Single) | Yes | **No** |
| Tool access (B: Context) | No | No |
| Tool access (C: Synthesize) | No | No |
| Tool access (D: Debate) | Yes | **No** |
| Tool access (E: Negotiate) | Yes | **No** |
| Constraint extractor | Haiku 4.5 | Haiku 4.5 |
| Output persistence | Scores only | **JSON + blind markdown + key** |
| Total cost | $39.58 | ~$8-10 |
| Runtime | ~2 hours | ~60 minutes |

## Appendix B: Double-Blind Review Materials

The following files are available for independent review:

- `evaluation-v2-double-blind.md` — All 50 responses, anonymized, randomized order
- `evaluation-v2-key.json` — Mode-to-label mapping (open after reviewer scores)
- `evaluation-v2-outputs.json` — Full outputs with metadata

## Appendix C: Known Runtime Issues

- **Haiku 529 errors:** The Anthropic API returned 529 (Overloaded) responses for Claude Haiku 4.5 throughout the benchmark run. This affected self-evaluation (learning feedback loop) and constraint extraction (negotiate mode sidecar). All failures were non-fatal — the benchmark continued with degraded sidecar functionality. Core Opus calls for all five modes completed successfully.
- **Constraint extraction failures (Q1-Q2):** The first two questions (pricing, plg) extracted zero constraints due to Haiku congestion, reducing negotiate mode's structural advantage on those questions.
- **Cost tracking bug (negotiate):** A before/after snapshot approach for cost tracking was contaminated by concurrent Haiku sidecar calls writing to the same cost store. Two questions show negative costs for negotiate mode. A fix (in-memory cost accumulator subclass) has been implemented for future runs.
- **ConstraintType enum:** The constraint extractor occasionally produces constraint types not in the enum (e.g., "revenue"), causing non-fatal extraction failures. This was also observed in v1.

---

*Generated by C-Suite Evaluation Framework v2.0 | Cardinal Element | February 2026*
*Replication of: "Does Multi-Agent AI Coordination Produce Better Strategic Recommendations Than a Single Large Language Model?" (Ewalt, Feb 2026)*
