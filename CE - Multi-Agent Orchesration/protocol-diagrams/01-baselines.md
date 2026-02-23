# Baselines (P1–P5)

## P1: Single Agent

**One agent receives the full prompt and produces a single response.**

### Summary Flow

```mermaid
graph LR
    U([User]):::agent -->|"prompt"| A([Agent]):::agent -->|"response"| O[Output]:::stage
    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"full prompt + constraints"| A([Single Agent]):::agent
    A --> P[Process: Analyze + Generate]:::stage
    P --> O[Final Output]:::stage

    subgraph Details
        direction TB
        D1["Agents: 1"]:::stage
        D2["Input: Full task prompt"]:::stage
        D3["Output: Single response"]:::stage
        D4["No aggregation needed"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P2: Single Agent + Context

**One agent with all C-Suite role context injected into system prompt.**

### Summary Flow

```mermaid
graph LR
    C[C-Suite Context]:::stage -->|"inject roles"| A([Agent]):::agent
    U([User]):::agent -->|"prompt"| A
    A -->|"response"| O[Output]:::stage
    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    C[Role Definitions:<br/>CEO, CFO, CTO, CMO, COO, CPO]:::stage
    U([User]):::agent -->|"task prompt"| SYS[System Prompt Assembly]:::stage
    C -->|"role context"| SYS
    SYS -->|"enriched prompt"| A([Single Agent]):::agent
    A --> P[Process with<br/>multi-perspective awareness]:::stage
    P --> O[Final Output]:::stage

    subgraph Details
        direction TB
        D1["Agents: 1"]:::stage
        D2["Input: Prompt + all role contexts"]:::stage
        D3["Output: Single response informed by all roles"]:::stage
        D4["Context window: Must fit all roles"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P3: Parallel Synthesis

**N agents work independently on the same prompt, then a synthesizer merges results.**

### Summary Flow

```mermaid
graph LR
    U([User]):::agent -->|"prompt"| A1([Agent 1]):::agent
    U -->|"prompt"| A2([Agent 2]):::agent
    U -->|"prompt"| AN([Agent N]):::agent
    A1 -->|"response 1"| S([Synthesizer]):::agent
    A2 -->|"response 2"| S
    AN -->|"response N"| S
    S -->|"merged output"| O[Output]:::stage
    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"identical prompt"| FAN[Fan-Out: Distribute to N agents]:::stage

    FAN --> A1([Agent 1<br/>e.g. CEO]):::agent
    FAN --> A2([Agent 2<br/>e.g. CTO]):::agent
    FAN --> AN([Agent N<br/>e.g. CFO]):::agent

    A1 -->|"independent<br/>analysis"| COLLECT[Collect All Responses]:::stage
    A2 -->|"independent<br/>analysis"| COLLECT
    AN -->|"independent<br/>analysis"| COLLECT

    COLLECT -->|"all N responses"| S([Synthesizer Agent]):::agent
    S --> MERGE[Merge: Identify<br/>agreements, conflicts,<br/>unique insights]:::stage
    MERGE --> O[Unified Output]:::stage

    subgraph Details
        direction TB
        D1["Agents: N workers + 1 synthesizer"]:::stage
        D2["Input per worker: Same prompt"]:::stage
        D3["Aggregation: Union of insights, conflict resolution"]:::stage
        D4["Decision: Synthesizer resolves disagreements"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P4: Multi-Round Debate

**Agents argue positions across 2 rounds, then a judge decides.**

### Summary Flow

```mermaid
graph LR
    A1([Agent A]):::agent <-->|"Round 1 + 2"| A2([Agent B]):::agent
    A1 -->|"arguments"| J([Judge]):::agent
    A2 -->|"arguments"| J
    J -->|"verdict"| O[Output]:::stage
    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"debate topic"| SETUP[Assign Positions]:::stage

    SETUP -->|"position A"| A([Debater A]):::agent
    SETUP -->|"position B"| B([Debater B]):::agent

    subgraph Round 1
        A -->|"opening argument"| R1A[Argument A1]:::stage
        B -->|"opening argument"| R1B[Argument B1]:::stage
    end

    R1A -->|"sees B1"| A
    R1B -->|"sees A1"| B

    subgraph Round 2
        A -->|"rebuttal"| R2A[Argument A2]:::stage
        B -->|"rebuttal"| R2B[Argument B2]:::stage
    end

    R2A --> JUDGE_IN[All Arguments<br/>A1 + B1 + A2 + B2]:::stage
    R2B --> JUDGE_IN
    JUDGE_IN -->|"full transcript"| J([Judge Agent]):::agent
    J --> EVAL{Evaluate:<br/>evidence quality,<br/>logical consistency,<br/>coverage}:::decision
    EVAL -->|"verdict + reasoning"| O[Final Decision]:::stage

    subgraph Details
        direction TB
        D1["Agents: 2 debaters + 1 judge"]:::stage
        D2["Rounds: 2 (opening + rebuttal)"]:::stage
        D3["Decision: Judge scores arguments on evidence, logic, coverage"]:::stage
        D4["Output: Verdict with rationale"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P5: Constraint Negotiation

**Agents propose solutions, a constraint checker filters them, iterate until convergence.**

### Summary Flow

```mermaid
graph LR
    A([Agents]):::agent -->|"proposals"| CC{Constraint<br/>Check}:::decision
    CC -->|"pass"| O[Output]:::stage
    CC -->|"fail + feedback"| A
    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"problem + constraints"| INIT[Initialize: Define<br/>hard & soft constraints]:::stage

    INIT -->|"constraints list"| CC([Constraint Checker]):::agent
    INIT -->|"problem"| AGENTS[Proposal Round]:::stage

    AGENTS --> A1([Agent 1]):::agent
    AGENTS --> A2([Agent 2]):::agent
    AGENTS --> AN([Agent N]):::agent

    A1 -->|"proposal"| COLLECT[Collect Proposals]:::stage
    A2 -->|"proposal"| COLLECT
    AN -->|"proposal"| COLLECT

    COLLECT -->|"all proposals"| CC
    CC --> EVAL{All hard<br/>constraints<br/>satisfied?}:::decision

    EVAL -->|"yes"| RANK[Rank by soft<br/>constraint satisfaction]:::stage
    EVAL -->|"no: specific<br/>violations listed"| FEEDBACK[Feedback:<br/>which constraints failed]:::stage
    FEEDBACK -->|"revise with<br/>violation details"| AGENTS

    RANK -->|"best proposal"| O[Final Output]:::stage

    subgraph Details
        direction TB
        D1["Agents: N proposers + 1 constraint checker"]:::stage
        D2["Iteration: Until hard constraints pass or max rounds"]:::stage
        D3["Filtering: Hard constraints = must pass; Soft = ranked"]:::stage
        D4["Output: Highest-ranked feasible proposal"]:::stage
    end

    classDef agent fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```
