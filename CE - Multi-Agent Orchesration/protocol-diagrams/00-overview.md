# Coordination Lab — 30 Protocol Visual Reference

---

## P0: Meta-Protocols — The Adaptive Router Layer

*These 3 patterns govern **which** of the 27 coordination protocols to run. Sourced from: Reasoning Router (2025), AgentiQL (NeurIPS 2025), TAO Framework.*

### P0a: Reasoning Router — Dynamic Strategy Selection

**A classifier agent analyzes the input problem's structural features and selects the optimal coordination protocol.**

```mermaid
graph TB
    U([User]):::agent -->|"query"| FEAT[Extract Feature Vector:<br/>complexity, ambiguity,<br/>risk, domain]:::stage

    FEAT --> CLASS([Classifier Agent<br/>— BERT or lightweight LLM]):::router

    CLASS --> EVAL{Problem Type?}:::decision

    EVAL -->|"multi-hop logic"| TOT["Route → Tree-of-Thoughts<br/>(e.g. P4 Debate)"]:::stage
    EVAL -->|"fact verification"| TOOL["Route → Tool-Augmented<br/>(e.g. P16 ACH)"]:::stage
    EVAL -->|"ideation needed"| DIV["Route → Divergent<br/>(e.g. P14 1-2-4-All)"]:::stage
    EVAL -->|"contradiction"| TRIZ["Route → TRIZ<br/>(P6)"]:::stage
    EVAL -->|"consensus needed"| VOTE["Route → Aggregation<br/>(e.g. P20 Borda)"]:::stage

    TOT --> EXEC[Execute Selected Protocol]:::stage
    TOOL --> EXEC
    DIV --> EXEC
    TRIZ --> EXEC
    VOTE --> EXEC

    EXEC --> O[Output]:::stage

    subgraph Details
        D1["Source: Reasoning Router (2025)"]:::stage
        D2["Classifier: Predicts best strategy from problem features"]:::stage
        D3["Key insight: Meta-reasoning — deciding HOW to think"]:::stage
        D4["Performance ceiling = router classification accuracy"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef router fill:#333,stroke:#111,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### P0b: Cost-Aware Skip Gate — When NOT to Use Multi-Agent

**A learned router decides whether the problem warrants a full multi-agent pipeline or a simple single-agent response, balancing accuracy vs. cost.**

```mermaid
graph TB
    U([User]):::agent -->|"query"| GATE([Skip Gate<br/>— Learned Router]):::router

    GATE --> ASSESS{Schema complexity?<br/>Query ambiguity?<br/>Stakes?}:::decision

    ASSESS -->|"low complexity"| SIMPLE([Single Agent<br/>— Fast Baseline]):::agent
    ASSESS -->|"high complexity"| FULL[Full Multi-Agent<br/>Pipeline]:::stage

    FULL --> SELECT[Select Protocol<br/>P1–P27]:::stage
    SELECT --> EXEC[Execute with<br/>N Agents]:::stage

    SIMPLE -->|"response"| O[Output]:::stage
    EXEC -->|"response"| O

    subgraph Details
        D1["Source: AgentiQL (NeurIPS 2025)"]:::stage
        D2["Gate: Learned cost/accuracy tradeoff"]:::stage
        D3["Saves compute on simple queries — 86% accuracy on Spider"]:::stage
        D4["Key insight: Not every problem needs a swarm"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef router fill:#333,stroke:#111,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### P0c: Tiered Escalation — Cascading Protocols on Failure

**Routes queries to the simplest adequate tier first. If confidence is low or errors detected, escalates to progressively more rigorous protocols.**

```mermaid
graph TB
    U([User]):::agent -->|"query"| T1[Tier 1: Fast Agent<br/>— Low latency, simple]:::stage

    T1 --> C1{Confidence ><br/>threshold?}:::decision
    C1 -->|"yes"| O[Output]:::stage
    C1 -->|"no: escalate"| T2[Tier 2: Multi-Agent<br/>— Moderate rigor<br/>e.g. P3 Parallel Synthesis]:::stage

    T2 --> C2{Consensus<br/>reached?}:::decision
    C2 -->|"yes"| O
    C2 -->|"no: escalate"| T3[Tier 3: Full Consensus<br/>— Max rigor<br/>e.g. P16 ACH or P4 Debate]:::stage

    T3 --> REVIEW([Oversight Agent]):::agent
    REVIEW --> C3{Passes<br/>safety check?}:::decision
    C3 -->|"yes"| O
    C3 -->|"fail: flag"| HUMAN[Flag for Human<br/>Review]:::stage

    subgraph Details
        D1["Source: TAO — Tiered Adaptive Oversight"]:::stage
        D2["Tier 1: Efficient but risky alone"]:::stage
        D3["Tier 3: Safe but expensive — used only when needed"]:::stage
        D4["Key insight: Router errors caught by escalation triggers"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef router fill:#333,stroke:#111,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## Legend

```mermaid
graph LR
    subgraph Legend
        A([Agent / Role]):::agent
        B[Processing Stage]:::stage
        C{Decision / Gate}:::decision
        D[(Data Store)]:::data
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff,rx:20
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
    classDef data fill:#7ED321,stroke:#5A9A18,color:#fff
```

**Arrow labels** indicate data or artifacts flowing between stages.

## Category Map

```mermaid
graph TB
    ROOT["30 Coordination Protocols"]:::root

    P0["Meta-Protocols<br/>P0a–P0c"]:::meta
    B["Baselines<br/>P1–P5"]:::baselines
    LS["Liberating Structures<br/>P6–P15"]:::libstruct
    IA["Intelligence Analysis<br/>P16–P18"]:::intel
    GT["Game Theory<br/>P19–P21"]:::gametheory
    OT["Org Theory<br/>P22–P23"]:::orgtheory
    ST["Systems Thinking<br/>P24–P25"]:::systems
    DT["Design Thinking<br/>P26–P27"]:::design

    ROOT --> P0
    ROOT --> B
    ROOT --> LS
    ROOT --> IA
    ROOT --> GT
    ROOT --> OT
    ROOT --> ST
    ROOT --> DT

    classDef root fill:#333,stroke:#111,color:#fff
    classDef meta fill:#607D8B,stroke:#455A64,color:#fff
    classDef baselines fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef libstruct fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef intel fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef gametheory fill:#F39C12,stroke:#D68910,color:#fff
    classDef orgtheory fill:#1ABC9C,stroke:#16A085,color:#fff
    classDef systems fill:#2ECC71,stroke:#27AE60,color:#fff
    classDef design fill:#E91E63,stroke:#C2185B,color:#fff
```

## Color Coding

| Category | Color | File |
|---|---|---|
| Meta-Protocols | Gray `#607D8B` | [00-overview.md](00-overview.md) (above) |
| Baselines | Blue `#4A90D9` | [01-baselines.md](01-baselines.md) |
| Liberating Structures | Purple `#9B59B6` | [02-liberating-structures.md](02-liberating-structures.md) |
| Intelligence Analysis | Red `#E74C3C` | [03-intelligence-analysis.md](03-intelligence-analysis.md) |
| Game Theory | Orange `#F39C12` | [04-game-theory.md](04-game-theory.md) |
| Org Theory | Teal `#1ABC9C` | [05-org-theory.md](05-org-theory.md) |
| Systems Thinking | Green `#2ECC71` | [06-systems-thinking.md](06-systems-thinking.md) |
| Design Thinking | Pink `#E91E63` | [07-design-thinking.md](07-design-thinking.md) |

## Full Protocol Index

| # | Protocol | Category | Agents | Key Mechanism |
|---|---|---|---|---|
| P0a | Reasoning Router | Meta-Protocol | 1 classifier | Classify problem features → select protocol |
| P0b | Cost-Aware Skip Gate | Meta-Protocol | 1 gate | Decide: single-agent vs. full pipeline |
| P0c | Tiered Escalation | Meta-Protocol | 1+ per tier | Tier 1 → Tier 2 → Tier 3 on failure |
| P1 | Single Agent | Baselines | 1 | Direct response |
| P2 | Single + Context | Baselines | 1 | Role context injection |
| P3 | Parallel Synthesis | Baselines | N+1 | Independent → merge |
| P4 | Multi-Round Debate | Baselines | N+1 | Argue → judge |
| P5 | Constraint Negotiation | Baselines | N+1 | Propose → filter → iterate |
| P6 | TRIZ Inversion | Liberating Structures | N+1 | Failure → invert |
| P7 | Wicked Questions | Liberating Structures | N+1 | Surface paradoxes |
| P8 | Min Specs | Liberating Structures | N+1 | Eliminate non-essentials |
| P9 | Troika Consulting | Liberating Structures | 3 | Client + consultants |
| P10 | HSR | Liberating Structures | N | Empathy translation |
| P11 | DAD | Liberating Structures | N+1 | Positive deviants |
| P12 | 25/10 Crowd Sourcing | Liberating Structures | N+1 | Blind scoring |
| P13 | Ecocycle Planning | Liberating Structures | N+1 | Lifecycle mapping |
| P14 | 1-2-4-All | Liberating Structures | N+1 | Progressive merging |
| P15 | What/So What/Now What | Liberating Structures | N+1 | Temporal frames |
| P16 | ACH | Intelligence Analysis | N+1 | Evidence matrix |
| P17 | Red/Blue/White Team | Intelligence Analysis | 3+ | Attack/defend/referee |
| P18 | Delphi Method | Intelligence Analysis | N+1 | Iterative convergence |
| P19 | Vickrey Auction | Game Theory | N+1 | Second-price bid |
| P20 | Borda Count | Game Theory | N+1 | Ranked aggregation |
| P21 | Interests-Based Negotiation | Game Theory | N+1 | Mutual gains |
| P22 | Sequential Pipeline | Org Theory | N | Chain processing |
| P23 | Cynefin Probe-Sense-Respond | Org Theory | N+1 | Domain classification |
| P24 | Causal Loop Mapping | Systems Thinking | N+1 | Feedback loops |
| P25 | System Archetype Detection | Systems Thinking | N+1 | Pattern matching |
| P26 | Crazy Eights | Design Thinking | N+1 | Constrained divergence |
| P27 | Affinity Mapping | Design Thinking | N+1 | Embedding clusters |
