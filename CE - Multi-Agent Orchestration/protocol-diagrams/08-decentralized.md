# Decentralized Coordination (P53–P57)

**Category color:** Steel `#16A2DA`

Five protocols where agents coordinate via shared state rather than through a central orchestrator judgment. The Python orchestrator is a pure tick scheduler — it advances ticks, formats Blackboard snapshots into prompts, and writes agent responses back verbatim. It does NOT synthesize content, filter contributions, or decide winners. All aggregation happens via deterministic math in `protocols/decentralized_actions.py`.

Every protocol reports its **four-dimension decentralization scorecard** (control / information / communication / termination) in its `capability.yaml`. Ship-honest — any dimension that's structurally centralized is named explicitly (e.g., P55's random pairing).

---

## P53: Contract Net Protocol

**Mechanism:** Announce → bid → Hungarian assignment → execute → concat.

```mermaid
graph TB
    Q[Question]:::stage --> SPLIT[Task Decomposition<br/>mechanical parse — 2-5 sub-tasks]:::mech
    SPLIT --> BOARD[(Blackboard:<br/>task_board)]:::bb

    BOARD --> B1([Agent 1 bid]):::agent
    BOARD --> B2([Agent 2 bid]):::agent
    BOARD --> B3([Agent N bid]):::agent

    B1 & B2 & B3 --> BIDS[(Blackboard:<br/>bids)]:::bb
    BIDS --> HUN[Hungarian assignment<br/>deterministic greedy]:::mech
    HUN --> AW[(Blackboard:<br/>awards)]:::bb

    AW --> E1([Awarded 1 executes]):::agent
    AW --> E2([Awarded 2 executes]):::agent
    AW --> E3([Awarded k executes]):::agent

    E1 & E2 & E3 --> D[(Blackboard:<br/>deliverables)]:::bb
    D --> ASM[Mechanical assembly<br/>concat in task-board order]:::mech
    ASM --> OUT[Final Report]:::stage

    classDef agent fill:#16A2DA,stroke:#0F7AA3,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef mech fill:#FFF4E0,stroke:#D4A017,color:#333
    classDef bb fill:#FAFAFA,stroke:#666,color:#111
```

**Scorecard:** control decentralized (self-bid) · information decentralized (shared task board) · communication via Blackboard · termination = deterministic quorum on awarded deliverables.

**When to use:** Task allocation, heterogeneous agents, multi-part questions. *"Who should own what?"*

---

## P54: Blackboard (Pandemonium) — Reference Implementation

**Mechanism:** Self-dispatched peer contribution. Every tick, every active agent sees the full Blackboard snapshot and independently chooses to contribute a new topic or halt.

```mermaid
graph LR
    Q[Question]:::stage --> BB0[(Blackboard<br/>seed: question only)]:::bb

    BB0 --> T1{{"Tick 1"}}:::stage
    T1 --> A1([Agent 1]):::agent
    T1 --> A2([Agent 2]):::agent
    T1 --> A3([Agent N]):::agent

    A1 -->|"contribute<br/>or halt"| BB1[(Blackboard)]:::bb
    A2 -->|"contribute<br/>or halt"| BB1
    A3 -->|"contribute<br/>or halt"| BB1

    BB1 --> CHK{All halted?}:::decision
    CHK -->|no| TN{{"Tick N"}}:::stage
    TN --> A1
    CHK -->|yes| ASM[Mechanical assembly<br/>group by topic, order by tick]:::mech
    ASM --> OUT[Final Report]:::stage

    classDef agent fill:#16A2DA,stroke:#0F7AA3,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef mech fill:#FFF4E0,stroke:#D4A017,color:#333
    classDef bb fill:#FAFAFA,stroke:#666,color:#111
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

**Scorecard:** all four dimensions distributed — control (self-dispatch each tick), information (full BB snapshot), communication (Blackboard), termination (all-halt + safety ceilings).

**When to use:** Ill-structured problems, emergent reasoning order, heterogeneous expertise, want full audit trail.

---

## P55: Gossip Consensus

**Mechanism:** Random-pair pairwise convergence to a numeric estimate. Variance predicate terminates.

```mermaid
graph TB
    Q[Question]:::stage --> R0([All agents<br/>initial estimate]):::agent
    R0 --> EST0[(Blackboard:<br/>estimates/round_0)]:::bb
    EST0 --> VAR0{variance &lt; ε?}:::decision
    VAR0 -->|yes| MEAN
    VAR0 -->|no| PAIR[Random pairing<br/>structural centralization]:::mech

    PAIR --> P1([Pair 1 exchange]):::agent
    PAIR --> P2([Pair 2 exchange]):::agent

    P1 & P2 --> ESTN[(Blackboard:<br/>estimates/round_N)]:::bb
    ESTN --> VARN{variance &lt; ε?}:::decision
    VARN -->|yes| MEAN
    VARN -->|no, &lt; max_rounds| PAIR
    VARN -->|no, max_rounds| MEAN

    MEAN[Confidence-weighted mean<br/>deterministic]:::mech --> OUT[Consensus Value]:::stage

    classDef agent fill:#16A2DA,stroke:#0F7AA3,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef mech fill:#FFF4E0,stroke:#D4A017,color:#333
    classDef bb fill:#FAFAFA,stroke:#666,color:#111
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

**Scorecard honest caveat:** control is **partially centralized** — random pairing is structural to gossip. Information is peer-local (pair only). Communication via BB. Termination = distributed variance predicate.

**When to use:** Numeric/probability estimates, organic convergence, belief aggregation without a judge.

---

## P56: Stigmergic Exploration

**Mechanism:** Pheromone-biased path convergence (ant-colony style). Decay, reinforce, explore.

```mermaid
graph TB
    Q[Question]:::stage --> SEED([Agents seed K paths<br/>pheromone=1.0 each]):::agent
    SEED --> PH0[(Blackboard:<br/>pheromone_map)]:::bb

    PH0 --> DEC[Mechanical decay<br/>p × decay_rate]:::mech
    DEC --> SHOW[Show pheromone map<br/>to all agents]:::stage
    SHOW --> T1([Each agent:<br/>reinforce / explore / halt]):::agent

    T1 --> PHN[(Blackboard:<br/>updated pheromone_map)]:::bb
    PHN --> TERM{top share &gt; θ<br/>OR all halt<br/>OR max_ticks?}:::decision
    TERM -->|no| DEC
    TERM -->|yes| TOPK[Top-K by pheromone<br/>deterministic rank]:::mech
    TOPK --> OUT[Convergence Report]:::stage

    classDef agent fill:#16A2DA,stroke:#0F7AA3,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef mech fill:#FFF4E0,stroke:#D4A017,color:#333
    classDef bb fill:#FAFAFA,stroke:#666,color:#111
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

**Scorecard:** all four dimensions distributed — control (self-select action), information (full pheromone map), communication (Blackboard), termination (dominance predicate + all-halt + safety).

**When to use:** Large solution spaces, strategy exploration, research-style questions where path-dependent reasoning matters.

---

## P57: Liquid Democracy

**Mechanism:** Each agent either ranks options directly OR delegates vote to a peer. Delegation chains resolve deterministically.

```mermaid
graph TB
    Q[Question]:::stage --> PROP([All agents<br/>propose 1-3 options]):::agent
    PROP --> RAW[(Blackboard:<br/>raw options)]:::bb
    RAW --> DEDUP[Mechanical dedup<br/>normalize + prefix cluster]:::mech
    DEDUP --> BALLOT[(Blackboard:<br/>ballot_options)]:::bb

    BALLOT --> VOTE([All agents<br/>vote OR delegate]):::agent
    VOTE --> V[(Blackboard:<br/>votes + delegations)]:::bb

    V --> RESOLVE[Resolve chains<br/>DFS, detect cycles]:::mech
    RESOLVE --> EFF[(Blackboard:<br/>effective_votes)]:::bb
    EFF --> BORDA[Weighted Borda<br/>deterministic]:::mech
    BORDA --> OUT[Winner verbatim<br/>no synthesis]:::stage

    classDef agent fill:#16A2DA,stroke:#0F7AA3,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef mech fill:#FFF4E0,stroke:#D4A017,color:#333
    classDef bb fill:#FAFAFA,stroke:#666,color:#111
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

**Scorecard:** all four dimensions distributed — control (vote-or-delegate choice), information (full ballot + peer list), communication (Blackboard), termination (distributed quorum on action).

**When to use:** Uneven expertise, want to surface who drove the decision, cross-domain questions.

---

## Decision Matrix

| Your situation | Use |
|---|---|
| "Who should own this?" (task allocation) | **P53 Contract Net** |
| Ill-structured emergent reasoning | **P54 Blackboard** |
| Numeric/probability convergence | **P55 Gossip Consensus** |
| Large strategy space, want exploration | **P56 Stigmergic Exploration** |
| Uneven expertise, weighted voting | **P57 Liquid Democracy** |

## Shared infrastructure

- `protocols/tick_scheduler.py` — `TickOrchestrator` base class (pure scheduler, no content judgment)
- `protocols/decentralized_actions.py` — Pydantic-style action dataclasses + deterministic aggregation helpers (Hungarian, Borda-with-delegation, variance, pheromone decay/dominance)
- `protocols/blackboard.py` — append-only shared state (pre-existing, previously dormant, now the substrate for all five)

Every protocol writes a `decentralization_manifest` entry to its Blackboard on init — inspection tools can assert the four-dimension claim against the run's actual behavior.
