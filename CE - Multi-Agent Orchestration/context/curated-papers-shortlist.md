# Curated Paper Shortlist — Coordination Lab

Source: Filtered from [awesome-multi-agent-papers](./awesome-multi-agent-papers.md) (235 papers → 27 curated)
Criteria: Direct relevance to protocol design, routing, debate mechanics, emergence, evaluation, topology, or simulation

---

## A. Debate & Deliberation Mechanics (P4, P5, P16-P18)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 22 | [Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate](https://arxiv.org/abs/2509.05396) | Directly validates/challenges our P4 debate protocol — identifies when debate hurts |
| 31 | [Rethinking the Bounds of LLM Reasoning: Are Multi-Agent Discussions the Key?](https://arxiv.org/pdf/2402.18272.pdf) | Empirical test of when discussion improves vs. degrades reasoning |
| 34 | [Multi-Agent Consensus Seeking via Large Language Models](https://arxiv.org/pdf/2310.20151.pdf) | Consensus dynamics — directly relevant to P5 constraint negotiation |
| 41 | [Unlocking the Power of Multi-Agent LLM for Reasoning: From Lazy Agents to Deliberation](https://arxiv.org/abs/2511.02303) | "Lazy agent" problem — agents converging too fast. Key risk for our debate protocol |
| 142 | [ChatEval: Towards Better LLM-based Evaluators through Multi-Agent Debate](https://arxiv.org/abs/2308.07201) | Multi-agent debate for evaluation — informs our judge protocol design |
| 145 | [Adversarial Multi-Agent Evaluation of Large Language Models through Iterative Debates](https://arxiv.org/pdf/2410.04663) | Adversarial debate structure — maps to P17 Red/Blue/White Team |

## B. Routing & Protocol Selection (P0a-P0c)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 44 | [RouteMoA: Dynamic Routing without Pre-Inference Boosts Efficient Mixture-of-Agents](https://arxiv.org/abs/2601.18130) | Dynamic routing across agent architectures — closest analog to our adaptive router |
| 59 | [TCAndon-Router: Adaptive Reasoning Router for Multi-Agent Collaboration](https://huggingface.co/papers/2601.04544) | Adaptive reasoning router — directly comparable to P0a Reasoning Router |
| 143 | [RouteLLM: An Open-Source Framework for Cost-Effective LLM Routing](https://lmsys.org/blog/2024-07-01-routellm/) | Cost-aware routing — informs our cost/quality tradeoff in router design |
| 14 | [Large Language Model Cascades with Mixture of Thoughts Representations for Cost-efficient Reasoning](https://arxiv.org/abs/2310.03094) | Cascade/escalation patterns — maps to P0c Tiered Escalation |

## C. Coordination Architecture & Topology (P3, P10, P14, P22)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 11 | [Mixture-of-Agents Enhances Large Language Model Capabilities](https://arxiv.org/abs/2406.04692) | MoA architecture — closest published analog to our P3 Parallel Synthesis |
| 10 | [Chain of Agents: Large Language Models Collaborating on Long-Context Tasks](https://arxiv.org/abs/2406.02818) | Sequential chain topology — maps to P22 Sequential Pipeline |
| 194 | [Talk Structurally, Act Hierarchically: A Collaborative Framework for LLM Multi-Agent Systems](https://arxiv.org/abs/2502.11098) | Hierarchical clustering topology — relevant to P14 1-2-4-All scaling structure |
| 58 | [Multi-Agent Collaboration via Evolving Orchestration](https://openreview.net/pdf/9727f658d788c52f49f12ae4b230baf4cf0d4007.pdf) | Evolving orchestration patterns — meta-learning which coordination works |
| 19 | [AGENTSNET: Coordination and Collaborative Reasoning in Multi-Agent LLMs](https://www.arxiv.org/abs/2507.08616) | Network-based coordination — directly relevant to Phase 6 topology analysis |

## D. Voting, Ranking & Collective Decision-Making (P12, P19, P20)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 206 | [LLM Voting: Human Choices and AI Collective Decision Making](https://api.semanticscholar.org/CorpusID:267413124) | Voting mechanics in LLM agents — maps to P20 Borda Count |
| 208 | [An Electoral Approach to Diversify LLM-based Multi-Agent Collective Decision-Making](https://api.semanticscholar.org/CorpusID:273502378) | Electoral/voting methods for agent decisions — validates P19-P20 game theory protocols |
| 135 | [Wisdom of the Silicon Crowd: LLM Ensemble Prediction Capabilities Match Human Crowd Accuracy](https://arxiv.org/abs/2402.19379) | Ensemble prediction accuracy — baseline for our P3 synthesis vs. single agent comparison |

## E. Failure Modes, Scaling & Evaluation (Cross-cutting)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 147 | [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/pdf/2503.13657) | Taxonomy of MAS failures — essential for interpreting our evaluation results |
| 54 | [The Collaboration Gap](https://huggingface.co/papers/2511.02687) | When collaboration doesn't help — informs our P0b Skip Gate design |
| 137 | [Are More LLM Calls All You Need? Towards Scaling Laws of Compound Inference Systems](https://arxiv.org/pdf/2403.02419.pdf) | Scaling laws for multi-agent — validates our cost/quality analysis |
| 43 | [Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) | Foundational scaling theory — informs Phase 6 simulation parameters |
| 4 | [More Agents is All You Need](https://arxiv.org/pdf/2402.05120.pdf) | Agent count scaling — baseline claim to test against our empirical data |

## F. Social Simulation & Emergence (Phase 4, Phase 6)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 160 | [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442) | Foundational ABM-with-LLMs paper — key reference for Phase 6 simulation design |
| 164 | [Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents](https://arxiv.org/abs/2404.16698) | Emergence of cooperation — directly relevant to Phase 4 emergence testing |
| 170 | [Cultural Evolution of Cooperation among LLM Agents](https://arxiv.org/pdf/2412.10270) | Cultural evolution dynamics — validates Centola-style contagion in LLM agents |
| 172 | [AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents](https://arxiv.org/abs/2502.08691v1) | Large-scale agent simulation framework — reference architecture for Phase 6 ABM |

## G. Already in Lit Review (Verify/Update)

| # | Paper | Why It Matters |
|---|-------|---------------|
| 89 | [MDAgents: An Adaptive Collaboration of LLMs for Medical Decision-Making](https://api.semanticscholar.org/CorpusID:269303028) | Already cited — adaptive complexity routing, validates our Cynefin-based router |
| 125 | [TRIZ Agents: A Multi-Agent LLM Approach for TRIZ-Based Innovation](https://doi.org/10.5220/0013321900003890) | Already cited — validates our P6 TRIZ Inversion protocol design |

---

## Download Priority

**Tier 1 — Read immediately** (core to protocol design & router):
#22, #44, #59, #147, #54, #11, #194, #19

**Tier 2 — Read before Phase 2 eval** (informs benchmarking):
#31, #41, #137, #4, #43, #135, #142, #206

**Tier 3 — Read before Phase 4-6** (emergence & simulation):
#160, #164, #170, #172, #34, #145, #208
