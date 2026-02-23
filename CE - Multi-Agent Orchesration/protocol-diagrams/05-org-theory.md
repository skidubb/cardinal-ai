# Organizational Theory (P22–P23)

## P22: Sequential Pipeline

**Agent A → Agent B → Agent C — each builds on prior output.**

### Summary Flow

```mermaid
graph LR
    A([Agent A]):::agent -->|"output A"| B([Agent B]):::agent -->|"output B"| C([Agent C]):::agent -->|"final"| O[Output]:::stage
    classDef agent fill:#1ABC9C,stroke:#16A085,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"initial input"| A([Agent A:<br/>e.g. Research]):::agent

    A --> PA[Process A:<br/>Generate raw material]:::stage
    PA -->|"output A +<br/>metadata"| B([Agent B:<br/>e.g. Analysis]):::agent

    B --> PB[Process B:<br/>Refine & structure<br/>using output A]:::stage
    PB -->|"output B +<br/>lineage"| C([Agent C:<br/>e.g. Synthesis]):::agent

    C --> PC[Process C:<br/>Final integration<br/>using outputs A + B]:::stage
    PC --> QA{Quality Gate:<br/>meets requirements?}:::decision
    QA -->|"pass"| O[Final Output<br/>with full lineage]:::stage
    QA -->|"fail: route back<br/>to specific stage"| REWORK[Identify failing stage<br/>and re-run from there]:::stage
    REWORK --> A

    subgraph Details
        D1["Agents: N in sequence (typically 3-5)"]:::stage
        D2["Each agent receives ALL prior outputs"]:::stage
        D3["Lineage tracking: Each output tagged with source"]:::stage
        D4["Output: Final product + processing lineage"]:::stage
    end

    classDef agent fill:#1ABC9C,stroke:#16A085,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P23: Cynefin Probe-Sense-Respond

**Classify the problem domain → run safe-to-fail probes → sense patterns → respond.**

### Summary Flow

```mermaid
graph LR
    CLASSIFY{Classify<br/>Domain}:::decision -->|"complex"| PROBE[Probe]:::stage
    PROBE --> SENSE[Sense]:::stage
    SENSE --> RESPOND[Respond]:::stage
    RESPOND --> O[Output]:::stage
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"problem"| CLASS{Phase 1: Classify<br/>Which Cynefin domain?}:::decision

    CLASS -->|"Clear"| CLEAR[Best Practice:<br/>Sense-Categorize-Respond]:::stage
    CLASS -->|"Complicated"| COMP[Expert Analysis:<br/>Sense-Analyze-Respond]:::stage
    CLASS -->|"Complex"| COMPLEX[Probe-Sense-Respond]:::stage
    CLASS -->|"Chaotic"| CHAOS[Act-Sense-Respond:<br/>Stabilize first]:::stage

    subgraph "Complex Domain Path (primary focus)"
        COMPLEX --> DESIGN[Design Safe-to-Fail<br/>Probes: Multiple small<br/>experiments]:::stage

        DESIGN --> P1([Probe Agent 1]):::agent
        DESIGN --> P2([Probe Agent 2]):::agent
        DESIGN --> P3([Probe Agent 3]):::agent

        P1 -->|"probe result"| SENSE2[Sense: Monitor for<br/>emergent patterns]:::stage
        P2 -->|"probe result"| SENSE2
        P3 -->|"probe result"| SENSE2

        SENSE2 --> EVAL{Patterns emerging?<br/>Amplify or dampen?}:::decision
        EVAL -->|"positive pattern"| AMP[Amplify:<br/>Scale what works]:::stage
        EVAL -->|"negative pattern"| DAMP[Dampen:<br/>Contain what fails]:::stage
        EVAL -->|"no pattern yet"| DESIGN

        AMP --> O[Response Strategy]:::stage
        DAMP --> O
    end

    subgraph Details
        D1["Agents: 1 classifier + N probe agents + 1 pattern sensor"]:::stage
        D2["Input: Problem that may be complex/uncertain"]:::stage
        D3["Decision: Domain classification drives approach"]:::stage
        D4["Output: Tested response strategy with evidence from probes"]:::stage
    end

    classDef agent fill:#1ABC9C,stroke:#16A085,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---
