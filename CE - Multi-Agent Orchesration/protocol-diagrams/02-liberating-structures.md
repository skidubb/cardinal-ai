# Liberating Structures (P6–P15)

## P6: TRIZ Inversion

**"What would guarantee failure?" — then invert to find solutions.**

### Summary Flow

```mermaid
graph LR
    U([User]):::agent -->|"challenge"| INV([Inversion Agents]):::agent
    INV -->|"failure list"| FLIP[Invert Failures]:::stage
    FLIP -->|"solutions"| S([Synthesizer]):::agent
    S --> O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"desired outcome"| Q[Reframe: How to<br/>guarantee failure?]:::stage
    Q -->|"inverted prompt"| A1([Agent 1]):::agent
    Q -->|"inverted prompt"| A2([Agent 2]):::agent
    Q -->|"inverted prompt"| AN([Agent N]):::agent

    A1 -->|"failure modes"| COLLECT[Collect All<br/>Failure Modes]:::stage
    A2 -->|"failure modes"| COLLECT
    AN -->|"failure modes"| COLLECT

    COLLECT --> DEDUP[Deduplicate &<br/>Categorize Failures]:::stage
    DEDUP --> INVERT[Invert Each Failure<br/>into Solution]:::stage
    INVERT --> RANK{Prioritize by<br/>impact & feasibility}:::decision
    RANK --> S([Synthesizer]):::agent
    S --> O[Actionable Solutions]:::stage

    subgraph Details
        D1["Agents: N generators + 1 synthesizer"]:::stage
        D2["Input: Inverted prompt — how to fail"]:::stage
        D3["Aggregation: Deduplicate failures, invert each"]:::stage
        D4["Output: Prioritized solution list"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P7: Wicked Questions

**Surface irresolvable paradoxes to sharpen strategic tensions.**

### Summary Flow

```mermaid
graph LR
    U([User]):::agent -->|"topic"| AG([Agents]):::agent
    AG -->|"paradoxes"| F{Filter:<br/>truly wicked?}:::decision
    F -->|"wicked questions"| O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"strategic topic"| FRAME[Frame: Identify<br/>competing demands]:::stage

    FRAME --> A1([Agent 1]):::agent
    FRAME --> A2([Agent 2]):::agent
    FRAME --> AN([Agent N]):::agent

    A1 -->|"tension pairs"| COLLECT[Collect All Tensions]:::stage
    A2 -->|"tension pairs"| COLLECT
    AN -->|"tension pairs"| COLLECT

    COLLECT --> TEST{Wickedness Test:<br/>1. Both sides true?<br/>2. Cannot choose one?<br/>3. Creates real tension?}:::decision
    TEST -->|"pass all 3"| FORMAT[Format as<br/>"How is it that X AND Y?"]:::stage
    TEST -->|"fail"| DISCARD[Discard: Not<br/>truly wicked]:::stage

    FORMAT --> RANK[Rank by<br/>strategic relevance]:::stage
    RANK --> O[Top Wicked Questions]:::stage

    subgraph Details
        D1["Agents: N generators + 1 evaluator"]:::stage
        D2["Input: Strategic topic or challenge"]:::stage
        D3["Filter: 3-part wickedness test"]:::stage
        D4["Output: Ranked paradoxes in question form"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P8: Min Specs

**Generate constraints, then progressively eliminate non-essential ones.**

### Summary Flow

```mermaid
graph LR
    U([User]):::agent -->|"goal"| GEN([Agents]):::agent
    GEN -->|"all specs"| ELIM{Eliminate<br/>non-essential}:::decision
    ELIM -->|"min specs"| O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"goal / purpose"| GEN[Generate: List ALL<br/>rules and constraints]:::stage

    GEN --> A1([Agent 1]):::agent
    GEN --> A2([Agent 2]):::agent
    GEN --> AN([Agent N]):::agent

    A1 -->|"spec list"| UNION[Union of<br/>All Specs]:::stage
    A2 -->|"spec list"| UNION
    AN -->|"spec list"| UNION

    UNION --> LOOP{For each spec:<br/>Would removing this<br/>make purpose impossible?}:::decision
    LOOP -->|"yes: keep"| MUST[Must-Have List]:::stage
    LOOP -->|"no: remove"| DROP[Remove Spec]:::stage

    DROP -->|"next spec"| LOOP
    MUST --> VOTE[Agents vote on<br/>borderline specs]:::stage
    VOTE --> O[Minimum Specification Set]:::stage

    subgraph Details
        D1["Agents: N generators + 1 facilitator"]:::stage
        D2["Input: Goal or purpose statement"]:::stage
        D3["Decision: Removal test — does purpose survive?"]:::stage
        D4["Output: Smallest set of absolute must-haves"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P9: Troika Consulting

**Client presents problem; 2 consultants discuss while client listens; client responds.**

### Summary Flow

```mermaid
graph LR
    CL([Client]):::agent -->|"problem"| C1([Consultant 1]):::agent
    CL -->|"problem"| C2([Consultant 2]):::agent
    C1 <-->|"discuss"| C2
    C1 -->|"advice"| CL
    C2 -->|"advice"| CL
    CL -->|"reflection"| O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    subgraph "Stage 1: Present"
        CL([Client Agent]):::agent -->|"problem statement<br/>+ context"| BRIEF[Brief to Consultants]:::stage
    end

    subgraph "Stage 2: Consult"
        BRIEF -->|"problem"| C1([Consultant 1]):::agent
        BRIEF -->|"problem"| C2([Consultant 2]):::agent
        C1 -->|"initial thoughts"| DISC[Open Discussion<br/>— Client LISTENS only]:::stage
        C2 -->|"initial thoughts"| DISC
        DISC --> C1
        DISC --> C2
        C1 -->|"refined advice"| ADV[Consolidated Advice]:::stage
        C2 -->|"refined advice"| ADV
    end

    subgraph "Stage 3: Reflect"
        ADV -->|"all advice"| CL
        CL --> REFL[Client Reflection:<br/>What resonated?<br/>What will I do?]:::stage
        REFL --> O[Action Plan]:::stage
    end

    subgraph Details
        D1["Agents: 1 client + 2 consultants (rotate roles)"]:::stage
        D2["Key rule: Client silent during consultation"]:::stage
        D3["Decision: Client chooses what to adopt"]:::stage
        D4["Output: Client's action plan"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P10: Heard-Seen-Respected (HSR)

**Empathy and translation between stakeholder perspectives.**

### Summary Flow

```mermaid
graph LR
    S1([Stakeholder A]):::agent -->|"experience"| L([Listener]):::agent
    L -->|"reflected back"| S1
    S2([Stakeholder B]):::agent -->|"experience"| L2([Listener]):::agent
    L2 -->|"reflected back"| S2
    S1 & S2 -->|"shared understanding"| O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"multi-stakeholder<br/>challenge"| ASSIGN[Assign Stakeholder<br/>Perspectives]:::stage

    ASSIGN --> SA([Agent A:<br/>Stakeholder View]):::agent
    ASSIGN --> SB([Agent B:<br/>Stakeholder View]):::agent

    subgraph "Phase 1: Share"
        SA -->|"experience narrative"| SHARE[Each shares their<br/>lived experience]:::stage
        SB -->|"experience narrative"| SHARE
    end

    subgraph "Phase 2: Reflect"
        SHARE --> RA[Agent A reflects back<br/>what B shared]:::stage
        SHARE --> RB[Agent B reflects back<br/>what A shared]:::stage
    end

    subgraph "Phase 3: Bridge"
        RA --> BRIDGE[Identify common<br/>ground & differences]:::stage
        RB --> BRIDGE
        BRIDGE --> TRANS[Translate concerns<br/>across perspectives]:::stage
    end

    TRANS --> O[Shared Understanding<br/>+ Translation Guide]:::stage

    subgraph Details
        D1["Agents: N stakeholder perspectives"]:::stage
        D2["Input: Challenge seen from different angles"]:::stage
        D3["Process: Share → Reflect back → Bridge"]:::stage
        D4["Output: Cross-perspective translation"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P11: Discovery & Action Dialogue (DAD)

**Find positive deviants — who's already succeeding? Extract transferable practices.**

### Summary Flow

```mermaid
graph LR
    U([User]):::agent -->|"problem"| SCAN([Scouts]):::agent
    SCAN -->|"positive deviants"| EXT[Extract Practices]:::stage
    EXT -->|"transferable actions"| O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"persistent problem"| Q1[Question: Who succeeds<br/>despite same constraints?]:::stage

    Q1 --> A1([Scout Agent 1]):::agent
    Q1 --> A2([Scout Agent 2]):::agent
    Q1 --> AN([Scout Agent N]):::agent

    A1 -->|"positive deviants<br/>+ their behaviors"| COLLECT[Collect Deviant<br/>Behaviors]:::stage
    A2 -->|"positive deviants<br/>+ their behaviors"| COLLECT
    AN -->|"positive deviants<br/>+ their behaviors"| COLLECT

    COLLECT --> FILTER{Is behavior:<br/>1. Uncommon?<br/>2. Accessible?<br/>3. Actually effective?}:::decision
    FILTER -->|"pass"| EXTRACT[Extract Core Practice]:::stage
    FILTER -->|"fail"| DISCARD[Discard]:::stage

    EXTRACT --> ADAPT[Adapt for<br/>target context]:::stage
    ADAPT --> O[Transferable<br/>Action Practices]:::stage

    subgraph Details
        D1["Agents: N scouts + 1 analyst"]:::stage
        D2["Input: Persistent problem with known constraints"]:::stage
        D3["Filter: Uncommon + accessible + effective"]:::stage
        D4["Output: Practices others can adopt"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P12: 25/10 Crowd Sourcing

**Rapid idea generation followed by blind scoring to surface top ideas.**

### Summary Flow

```mermaid
graph LR
    AG([All Agents]):::agent -->|"ideas"| SCORE{Blind<br/>Score}:::decision
    SCORE -->|"top ideas"| O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"challenge"| GEN[Phase 1: Generate<br/>— each agent writes<br/>bold idea on 'card']:::stage

    GEN --> A1([Agent 1]):::agent
    GEN --> A2([Agent 2]):::agent
    GEN --> AN([Agent N]):::agent

    A1 -->|"idea card"| POOL[Idea Pool<br/>— anonymized]:::stage
    A2 -->|"idea card"| POOL
    AN -->|"idea card"| POOL

    POOL --> ROUND["Phase 2: Score<br/>5 rounds of blind<br/>1-5 scoring"]:::stage

    ROUND --> A1S([Agent 1<br/>scores random card]):::agent
    ROUND --> A2S([Agent 2<br/>scores random card]):::agent
    ROUND --> ANS([Agent N<br/>scores random card]):::agent

    A1S -->|"score"| TALLY[Tally All Scores]:::stage
    A2S -->|"score"| TALLY
    ANS -->|"score"| TALLY

    TALLY --> RANK[Rank by<br/>total score]:::stage
    RANK --> TOP[Top 25% Ideas]:::stage
    TOP --> O[Winning Ideas<br/>+ Scores]:::stage

    subgraph Details
        D1["Agents: N (all generate AND score)"]:::stage
        D2["Scoring: Blind, 1-5 scale, 5 rounds"]:::stage
        D3["Aggregation: Sum scores per idea"]:::stage
        D4["Output: Ranked ideas, top 25% highlighted"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P13: Ecocycle Planning

**Map initiatives to lifecycle stages: birth, maturity, creative destruction, renewal.**

### Summary Flow

```mermaid
graph LR
    AG([Agents]):::agent -->|"initiatives"| MAP[Map to<br/>Lifecycle]:::stage
    MAP -->|"categorized"| ACT{Action per<br/>stage}:::decision
    ACT --> O[Output]:::stage
    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"portfolio of<br/>initiatives"| LIST[List All Current<br/>Initiatives]:::stage

    LIST --> A1([Agent 1]):::agent
    LIST --> A2([Agent 2]):::agent
    LIST --> AN([Agent N]):::agent

    A1 -->|"stage assignments"| COLLECT[Collect<br/>Assessments]:::stage
    A2 -->|"stage assignments"| COLLECT
    AN -->|"stage assignments"| COLLECT

    COLLECT --> CONSENSUS[Consensus: Resolve<br/>disagreements on<br/>stage placement]:::stage

    CONSENSUS --> BIRTH["Birth / Startup:<br/>Invest & nurture"]:::stage
    CONSENSUS --> MATURE["Maturity:<br/>Optimize & scale"]:::stage
    CONSENSUS --> DESTRUCT["Creative Destruction:<br/>Sunset & harvest"]:::stage
    CONSENSUS --> RENEW["Renewal:<br/>Repurpose & reimagine"]:::stage

    BIRTH --> PLAN[Action Plan<br/>per Initiative]:::stage
    MATURE --> PLAN
    DESTRUCT --> PLAN
    RENEW --> PLAN
    PLAN --> O[Portfolio Strategy]:::stage

    subgraph Details
        D1["Agents: N assessors + 1 facilitator"]:::stage
        D2["Input: List of initiatives/projects"]:::stage
        D3["Framework: 4-stage lifecycle (birth → maturity → destruction → renewal)"]:::stage
        D4["Output: Stage assignment + action per initiative"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P14: 1-2-4-All

**Progressive merging: solo ideation → pairs → quads → all synthesize.**

### Summary Flow

```mermaid
graph LR
    SOLO["1: Solo"]:::stage --> PAIR["2: Pairs"]:::stage
    PAIR --> QUAD["4: Quads"]:::stage
    QUAD --> ALL["All: Synthesize"]:::stage
    ALL --> O[Output]:::stage
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"prompt"| S1["Stage 1 — Solo<br/>Each agent generates<br/>ideas independently"]:::stage

    S1 --> A1([Agent 1]):::agent
    S1 --> A2([Agent 2]):::agent
    S1 --> A3([Agent 3]):::agent
    S1 --> A4([Agent 4]):::agent

    subgraph "Stage 2 — Pairs"
        A1 -->|"ideas"| P1[Pair 1 Merge:<br/>Find shared themes]:::stage
        A2 -->|"ideas"| P1
        A3 -->|"ideas"| P2[Pair 2 Merge:<br/>Find shared themes]:::stage
        A4 -->|"ideas"| P2
    end

    subgraph "Stage 3 — Quads"
        P1 -->|"pair themes"| Q1[Quad Merge:<br/>Refine & prioritize]:::stage
        P2 -->|"pair themes"| Q1
    end

    subgraph "Stage 4 — All"
        Q1 -->|"quad output"| SYNTH([Synthesizer]):::agent
        SYNTH --> O[Final Unified Output]:::stage
    end

    subgraph Details
        D1["Agents: N (ideally power of 2) + 1 synthesizer"]:::stage
        D2["Stages: 4 progressive merges (1→2→4→all)"]:::stage
        D3["Each merge: Find common themes, resolve conflicts"]:::stage
        D4["Output: Progressively refined consensus"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

---

## P15: What / So What / Now What

**Three temporal frames: observations → implications → actions.**

### Summary Flow

```mermaid
graph LR
    WHAT["What?<br/>Observations"]:::stage --> SO["So What?<br/>Implications"]:::stage
    SO --> NOW["Now What?<br/>Actions"]:::stage
    NOW --> O[Output]:::stage
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"experience / data"| PH1["Phase 1 — WHAT<br/>What happened?<br/>What did you observe?"]:::stage

    PH1 --> A1([Agent 1]):::agent
    PH1 --> A2([Agent 2]):::agent
    PH1 --> AN([Agent N]):::agent

    A1 -->|"observations"| OBS[Collect Observations]:::stage
    A2 -->|"observations"| OBS
    AN -->|"observations"| OBS

    OBS --> PH2["Phase 2 — SO WHAT<br/>Why does this matter?<br/>What patterns emerge?"]:::stage

    PH2 --> A1B([Agent 1]):::agent
    PH2 --> A2B([Agent 2]):::agent
    PH2 --> ANB([Agent N]):::agent

    A1B -->|"implications"| IMP[Collect Implications]:::stage
    A2B -->|"implications"| IMP
    ANB -->|"implications"| IMP

    IMP --> PH3["Phase 3 — NOW WHAT<br/>What actions follow?<br/>Next steps?"]:::stage

    PH3 --> A1C([Agent 1]):::agent
    PH3 --> A2C([Agent 2]):::agent
    PH3 --> ANC([Agent N]):::agent

    A1C -->|"actions"| ACT[Collect Actions]:::stage
    A2C -->|"actions"| ACT
    ANC -->|"actions"| ACT

    ACT --> SYNTH([Synthesizer]):::agent
    SYNTH --> O[Structured Output:<br/>Observations → Implications → Actions]:::stage

    subgraph Details
        D1["Agents: N per phase + 1 synthesizer"]:::stage
        D2["Phases: 3 sequential (What → So What → Now What)"]:::stage
        D3["Each phase feeds into the next"]:::stage
        D4["Output: Three-layer structured analysis"]:::stage
    end

    classDef agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```
