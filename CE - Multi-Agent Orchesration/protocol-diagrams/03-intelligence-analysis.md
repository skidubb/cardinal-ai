# Intelligence Analysis (P16–P18)

## P16: Analysis of Competing Hypotheses (ACH)

**Generate hypotheses, score evidence for/against each, eliminate least supported.**

### Summary Flow

```mermaid
graph LR
    AG([Agents]):::agent -->|"hypotheses"| MAT[Evidence<br/>Matrix]:::stage
    MAT -->|"scores"| ELIM{Eliminate<br/>weakest}:::decision
    ELIM -->|"surviving hypotheses"| O[Output]:::stage
    classDef agent fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"intelligence question"| PH1[Phase 1: Generate<br/>all plausible hypotheses]:::stage

    PH1 --> A1([Analyst 1]):::agent
    PH1 --> A2([Analyst 2]):::agent
    PH1 --> AN([Analyst N]):::agent

    A1 -->|"hypotheses"| HPOOL[Hypothesis Pool<br/>H1, H2, ... Hk]:::stage
    A2 -->|"hypotheses"| HPOOL
    AN -->|"hypotheses"| HPOOL

    HPOOL --> PH2[Phase 2: List all<br/>available evidence]:::stage
    PH2 --> ELIST[Evidence List<br/>E1, E2, ... Em]:::stage

    ELIST --> PH3[Phase 3: Build Matrix<br/>Each agent scores each<br/>E against each H]:::stage

    PH3 --> MATRIX["Evidence-Hypothesis Matrix<br/>Score: Consistent (C) /<br/>Inconsistent (I) / Neutral (N)"]:::stage

    MATRIX --> PH4{Phase 4: Eliminate<br/>hypotheses with most<br/>Inconsistent evidence}:::decision

    PH4 -->|"eliminated"| REMOVED[Rejected Hypotheses]:::stage
    PH4 -->|"surviving"| SENSITIVITY[Phase 5: Sensitivity<br/>Analysis — which evidence<br/>is most diagnostic?]:::stage

    SENSITIVITY --> O[Surviving Hypotheses<br/>+ Key Evidence<br/>+ Confidence Level]:::stage

    subgraph Details
        D1["Agents: N analysts + 1 matrix coordinator"]:::stage
        D2["Input: Intelligence question + available evidence"]:::stage
        D3["Decision: Eliminate by inconsistency count, NOT confirmation count"]:::stage
        D4["Output: Ranked hypotheses with diagnostic evidence identified"]:::stage
    end

    classDef agent fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P17: Red / Blue / White Team

**Red attacks, Blue defends, White referees.**

### Summary Flow

```mermaid
graph LR
    R([Red Team]):::agent -->|"attacks"| W([White Team]):::agent
    B([Blue Team]):::agent -->|"defenses"| W
    W -->|"assessment"| O[Output]:::stage
    classDef agent fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"strategy / plan<br/>to stress-test"| SETUP[Assign Teams]:::stage

    SETUP -->|"find flaws"| R([Red Team<br/>— Adversary]):::agent
    SETUP -->|"defend plan"| B([Blue Team<br/>— Defender]):::agent
    SETUP -->|"referee"| W([White Team<br/>— Arbiter]):::agent

    subgraph "Round 1: Attack"
        R -->|"vulnerabilities,<br/>failure modes,<br/>blind spots"| ATTACKS[Attack Report]:::stage
    end

    subgraph "Round 2: Defend"
        ATTACKS -->|"attacks to address"| B
        B -->|"mitigations,<br/>counterarguments,<br/>evidence"| DEFENSE[Defense Report]:::stage
    end

    subgraph "Round 3: Adjudicate"
        ATTACKS --> W
        DEFENSE --> W
        W --> EVAL{For each attack:<br/>Defense adequate?}:::decision
        EVAL -->|"yes"| RESOLVED[Resolved Risks]:::stage
        EVAL -->|"no"| OPEN[Open Risks<br/>— need action]:::stage
    end

    RESOLVED --> O[Final Assessment:<br/>Resolved + Open Risks<br/>+ Recommendations]:::stage
    OPEN --> O

    subgraph Details
        D1["Agents: 1+ Red, 1+ Blue, 1 White"]:::stage
        D2["Input: Strategy or plan to stress-test"]:::stage
        D3["Decision: White evaluates if defenses address attacks"]:::stage
        D4["Output: Risk register with resolution status"]:::stage
    end

    classDef agent fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P18: Delphi Method

**Independent estimates → share reasoning → re-estimate → converge.**

### Summary Flow

```mermaid
graph LR
    AG([Experts]):::agent -->|"estimates"| SHARE[Share<br/>Reasoning]:::stage
    SHARE -->|"re-estimate"| AG
    AG -->|"converged"| O[Output]:::stage
    classDef agent fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"estimation question"| R1[Round 1: Independent<br/>Estimates]:::stage

    R1 --> A1([Expert 1]):::agent
    R1 --> A2([Expert 2]):::agent
    R1 --> AN([Expert N]):::agent

    A1 -->|"estimate + reasoning"| C1[Collect Round 1]:::stage
    A2 -->|"estimate + reasoning"| C1
    AN -->|"estimate + reasoning"| C1

    C1 --> STATS1[Compute: Median,<br/>IQR, Spread]:::stage
    STATS1 --> SHARE1[Share: Anonymous<br/>summary + all reasoning]:::stage

    SHARE1 --> R2[Round 2: Revise<br/>Estimates]:::stage

    R2 --> A1B([Expert 1]):::agent
    R2 --> A2B([Expert 2]):::agent
    R2 --> ANB([Expert N]):::agent

    A1B -->|"revised estimate<br/>+ updated reasoning"| C2[Collect Round 2]:::stage
    A2B -->|"revised estimate<br/>+ updated reasoning"| C2
    ANB -->|"revised estimate<br/>+ updated reasoning"| C2

    C2 --> CONV{Convergence test:<br/>IQR < threshold?}:::decision
    CONV -->|"yes"| O[Final Estimate:<br/>Median + Confidence<br/>Interval]:::stage
    CONV -->|"no"| SHARE2[Share & run<br/>another round]:::stage
    SHARE2 --> R2

    subgraph Details
        D1["Agents: N experts (anonymous to each other)"]:::stage
        D2["Rounds: 2-4 until convergence"]:::stage
        D3["Convergence: IQR below threshold or max rounds"]:::stage
        D4["Output: Median estimate + confidence interval + reasoning summary"]:::stage
    end

    classDef agent fill:#E74C3C,stroke:#C0392B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```
