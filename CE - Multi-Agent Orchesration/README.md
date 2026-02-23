# The Coordination Lab

**Empirical validation of 30 multi-agent coordination protocols across 8 problem types — building toward an adaptive router that selects the optimal protocol for any strategic question.**

Scott Ewalt | [Cardinal Element](https://cardinalelement.com) | February 2026

---

## What This Is

A systematic research program to answer: *which coordination architecture works best for which kind of strategic problem?*

We're testing 30 protocols drawn from five coordination traditions against 32 benchmark questions, with tool-access as a controlled variable. The end goal is an **adaptive router** for Cardinal Element's C-Suite multi-agent advisory product that automatically selects the right protocol based on problem characteristics.

## Problem Types

| # | Type | Core Challenge |
|---|------|----------------|
| 1 | **Integration** | Combine multiple valid perspectives into a coherent plan |
| 2 | **Adversarial** | Stress-test assumptions under competitive pressure |
| 3 | **Stakeholder Tension** | Satisfy competing parties with hard constraints |
| 4 | **Diagnostic** | Identify root cause of underperformance |
| 5 | **Exploration** | Generate novel options in open-ended space |
| 6 | **Prioritization** | Rank competing valid options defensibly |
| 7 | **Paradox/Wicked** | Sharpen irresolvable tensions for management |
| 8 | **Risk/Pre-Mortem** | Identify failure modes in an accepted plan |

## 30 Protocols

| Category | Protocols | Source Tradition |
|----------|-----------|-----------------|
| **Meta-Protocols** (P0a-c) | Reasoning Router, Skip Gate, Tiered Escalation | Adaptive routing / Cynefin |
| **Baselines** (P1-P5) | Single Agent, Single+Context, Parallel Synthesis, Debate, Constraint Negotiation | Control group |
| **Liberating Structures** (P6-P15) | TRIZ, Wicked Questions, Min Specs, Troika, HSR, DAD, 25/10, Ecocycle, 1-2-4-All, What/So What/Now What | Lipmanowicz & McCandless |
| **Intelligence Analysis** (P16-P18) | ACH, Red/Blue/White Team, Delphi Method | IC tradecraft |
| **Game Theory** (P19-P21) | Vickrey Auction, Borda Count, Interests-Based Negotiation | Mechanism design |
| **Org Theory** (P22-P23) | Sequential Pipeline, Cynefin Probe-Sense-Respond | Snowden, process eng. |
| **Systems Thinking** (P24-P25) | Causal Loop Mapping, System Archetype Detection | Senge, Meadows |
| **Design Thinking** (P26-P27) | Crazy Eights, Affinity Mapping | IDEO, d.school |

## Repo Structure

```
├── The Coordination Lab *.md        # Master research spec (taxonomy, protocols, roadmap)
├── Deep Research - multiagent teams.txt  # Literature review (2024-2026 papers)
├── protocol-visualization.html      # Interactive protocol browser (standalone HTML)
└── protocol-diagrams/
    ├── 00-overview.md               # Meta-protocols (P0a-c) + index
    ├── 01-baselines.md              # P1-P5
    ├── 02-liberating-structures.md  # P6-P15
    ├── 03-intelligence-analysis.md  # P16-P18
    ├── 04-game-theory.md            # P19-P21
    ├── 05-org-theory.md             # P22-P23
    ├── 06-systems-thinking.md       # P24-P25
    └── 07-design-thinking.md        # P26-P27
```

## Key References

The literature review cites these foundational papers:

- **Reasoning Router** (2025) — Dynamic multi-strategy reasoning for robust problem solving
- **AgentiQL** (NeurIPS 2025) — Agent-inspired multi-expert architecture with learned routing
- **TAO Framework** — Tiered Adaptive Oversight for safety-critical routing
- **TRIZ Agents** (ICAART 2025) — Multi-agent LLM approach for TRIZ-based innovation
- **AgentCDM** (2025) — ACH-inspired structured reasoning for multi-agent decision-making
- **HypoAgents** — Hypothesis-driven multi-agent reasoning
- **MDAgents** — Medical decision-making with adaptive agent coordination

## Research Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | 30 protocols × 8 problem types (32 benchmark questions) | Designed |
| **Phase 2** | Extend to supplemental types 9-12, refine router | Planned |
| **Phase 3** | Full matrix with tool-access as controlled variable | Planned |
| **Phase 4** | Production adaptive router from empirical results | Planned |

## License

Proprietary — Cardinal Element, 2026.
