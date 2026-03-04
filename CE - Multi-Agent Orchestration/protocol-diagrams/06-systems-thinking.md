# Systems Thinking (P24–P25)

## P24: Causal Loop Mapping

**Extract variables → identify causal links → find reinforcing and balancing loops.**

### Summary Flow

```mermaid
graph LR
    AG([Agents]):::agent -->|"variables +<br/>relationships"| MAP[Build Causal<br/>Loop Diagram]:::stage
    MAP -->|"loops identified"| O[Output]:::stage
    classDef agent fill:#2ECC71,stroke:#27AE60,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"system description"| PH1[Phase 1: Extract<br/>Key Variables]:::stage

    PH1 --> A1([Agent 1]):::agent
    PH1 --> A2([Agent 2]):::agent
    PH1 --> AN([Agent N]):::agent

    A1 -->|"variable list"| VARS[Merge & Deduplicate<br/>Variables]:::stage
    A2 -->|"variable list"| VARS
    AN -->|"variable list"| VARS

    VARS --> PH2[Phase 2: Identify<br/>Causal Links]:::stage

    PH2 --> A1B([Agent 1]):::agent
    PH2 --> A2B([Agent 2]):::agent
    PH2 --> ANB([Agent N]):::agent

    A1B -->|"A causes B (+/-)"| LINKS[Merge All<br/>Causal Links]:::stage
    A2B -->|"links"| LINKS
    ANB -->|"links"| LINKS

    LINKS --> PH3[Phase 3: Trace Loops]:::stage
    PH3 --> DETECT{Detect loop type}:::decision

    DETECT -->|"all + links"| R["Reinforcing Loop (R):<br/>Amplifying feedback"]:::stage
    DETECT -->|"has - link"| B["Balancing Loop (B):<br/>Stabilizing feedback"]:::stage

    R --> DIAGRAM[Causal Loop Diagram<br/>with R and B labels]:::stage
    B --> DIAGRAM

    DIAGRAM --> LEVER[Identify Leverage<br/>Points: Where to<br/>intervene]:::stage
    LEVER --> O[CLD + Leverage<br/>Point Analysis]:::stage

    subgraph Details
        D1["Agents: N variable extractors + 1 loop analyst"]:::stage
        D2["Input: System description or problem narrative"]:::stage
        D3["Detection: Trace closed paths, count polarity"]:::stage
        D4["Output: Causal loop diagram + leverage points"]:::stage
    end

    classDef agent fill:#2ECC71,stroke:#27AE60,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P25: System Archetype Detection

**Match observed dynamics to known archetypes (Fixes That Fail, Shifting the Burden, etc.).**

### Summary Flow

```mermaid
graph LR
    AG([Agents]):::agent -->|"dynamics"| MATCH{Match to<br/>Archetype}:::decision
    MATCH -->|"archetype + leverage"| O[Output]:::stage
    classDef agent fill:#2ECC71,stroke:#27AE60,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"situation description"| PH1[Phase 1: Describe<br/>Observed Dynamics]:::stage

    PH1 --> A1([Agent 1]):::agent
    PH1 --> A2([Agent 2]):::agent
    PH1 --> AN([Agent N]):::agent

    A1 -->|"dynamic patterns"| DYN[Collect Observed<br/>Dynamics & Patterns]:::stage
    A2 -->|"dynamic patterns"| DYN
    AN -->|"dynamic patterns"| DYN

    DYN --> PH2[Phase 2: Compare to<br/>Known Archetypes]:::stage

    PH2 --> LIB["Archetype Library:<br/>- Fixes That Fail<br/>- Shifting the Burden<br/>- Limits to Growth<br/>- Eroding Goals<br/>- Escalation<br/>- Success to Successful<br/>- Tragedy of Commons<br/>- Growth & Underinvestment"]:::stage

    LIB --> MATCH{Match Score:<br/>How well does each<br/>archetype fit?}:::decision

    MATCH -->|"best match(es)"| EXPLAIN[Explain Match:<br/>Map situation elements<br/>to archetype structure]:::stage

    EXPLAIN --> LEVER[Archetype-Specific<br/>Leverage Points &<br/>Interventions]:::stage
    LEVER --> O[Matched Archetype(s)<br/>+ Structural Explanation<br/>+ Intervention Strategy]:::stage

    subgraph Details
        D1["Agents: N pattern observers + 1 archetype matcher"]:::stage
        D2["Input: Situation with recurring problematic dynamics"]:::stage
        D3["Library: 8+ standard system archetypes"]:::stage
        D4["Output: Best-fit archetype + structural map + interventions"]:::stage
    end

    classDef agent fill:#2ECC71,stroke:#27AE60,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---
