# Game Theory (P19–P21)

## P19: Vickrey Auction

**Sealed bids with confidence scores. Winner pays second-highest price. Prevents overconfidence.**

### Summary Flow

```mermaid
graph LR
    AG([Bidder Agents]):::agent -->|"sealed bids"| AUC{Auction:<br/>highest bid wins,<br/>pays 2nd price}:::decision
    AUC -->|"winner + cost"| O[Output]:::stage
    classDef agent fill:#F39C12,stroke:#D68910,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"options to evaluate"| SETUP[Present Options<br/>+ Evaluation Criteria]:::stage

    SETUP --> A1([Agent 1]):::agent
    SETUP --> A2([Agent 2]):::agent
    SETUP --> AN([Agent N]):::agent

    subgraph "Phase 1: Sealed Bidding"
        A1 -->|"bid: option + confidence<br/>(sealed, simultaneous)"| BIDS[Sealed Bid Box]:::stage
        A2 -->|"bid: option + confidence"| BIDS
        AN -->|"bid: option + confidence"| BIDS
    end

    BIDS --> REVEAL[Reveal All Bids<br/>Simultaneously]:::stage

    REVEAL --> RANK{Rank by<br/>confidence score}:::decision
    RANK --> WINNER[Winner: Highest bid<br/>BUT pays 2nd-highest<br/>confidence cost]:::stage

    WINNER --> JUSTIFY[Winner must justify<br/>at 2nd-price confidence<br/>level, not their own]:::stage

    JUSTIFY --> O[Selected Option<br/>+ Calibrated Confidence<br/>+ Justification]:::stage

    subgraph Details
        D1["Agents: N bidders + 1 auctioneer"]:::stage
        D2["Mechanism: Second-price auction prevents overbidding"]:::stage
        D3["Confidence calibration: Winner argues at lower bar"]:::stage
        D4["Output: Best option with calibrated confidence"]:::stage
    end

    classDef agent fill:#F39C12,stroke:#D68910,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P20: Borda Count Voting

**Agents rank all options; points aggregated across rankings.**

### Summary Flow

```mermaid
graph LR
    AG([Voter Agents]):::agent -->|"ranked ballots"| COUNT[Borda<br/>Count]:::stage
    COUNT -->|"winner"| O[Output]:::stage
    classDef agent fill:#F39C12,stroke:#D68910,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"K options to rank"| PRESENT[Present All Options<br/>with Context]:::stage

    PRESENT --> A1([Voter 1]):::agent
    PRESENT --> A2([Voter 2]):::agent
    PRESENT --> AN([Voter N]):::agent

    subgraph "Phase 1: Rank"
        A1 -->|"ranking: 1st, 2nd, ... Kth<br/>+ reasoning per rank"| BALLOTS[Collect Ballots]:::stage
        A2 -->|"ranking + reasoning"| BALLOTS
        AN -->|"ranking + reasoning"| BALLOTS
    end

    subgraph "Phase 2: Score"
        BALLOTS --> POINTS["Assign Borda Points:<br/>1st place = K-1 pts<br/>2nd place = K-2 pts<br/>... Last = 0 pts"]:::stage
        POINTS --> TALLY[Sum Points<br/>per Option]:::stage
    end

    subgraph "Phase 3: Analyze"
        TALLY --> RANK{Clear winner<br/>or tie?}:::decision
        RANK -->|"clear winner"| WINNER[Winner + Margin]:::stage
        RANK -->|"tie"| TIEBREAK[Tiebreak: Compare<br/>head-to-head preferences]:::stage
        TIEBREAK --> WINNER
    end

    WINNER --> REPORT[Report: Rankings,<br/>scores, reasoning<br/>clusters]:::stage
    REPORT --> O[Selected Option<br/>+ Consensus Analysis]:::stage

    subgraph Details
        D1["Agents: N voters + 1 tallier"]:::stage
        D2["Scoring: Borda count (positional voting)"]:::stage
        D3["Tiebreak: Condorcet head-to-head if needed"]:::stage
        D4["Output: Winner + full ranking + reasoning themes"]:::stage
    end

    classDef agent fill:#F39C12,stroke:#D68910,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P21: Interests-Based Negotiation

**Surface interests (not positions) → generate mutual gains → commit.**

### Summary Flow

```mermaid
graph LR
    AG([Negotiators]):::agent -->|"interests"| GEN[Generate<br/>Options]:::stage
    GEN -->|"mutual gains"| COMMIT{Commit?}:::decision
    COMMIT -->|"agreement"| O[Output]:::stage
    classDef agent fill:#F39C12,stroke:#D68910,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"negotiation scenario"| PH1[Phase 1: Surface Interests<br/>— NOT positions]:::stage

    PH1 --> A1([Party A]):::agent
    PH1 --> A2([Party B]):::agent

    subgraph "Phase 1: Interests"
        A1 -->|"underlying interests,<br/>needs, fears, priorities"| INT[Interest Map]:::stage
        A2 -->|"underlying interests,<br/>needs, fears, priorities"| INT
    end

    INT --> SHARED{Identify:<br/>Shared interests?<br/>Compatible interests?<br/>Conflicting interests?}:::decision

    subgraph "Phase 2: Generate Options"
        SHARED --> BRAINSTORM[Brainstorm Options<br/>that satisfy multiple<br/>interests simultaneously]:::stage
        A1 -->|"options"| BRAINSTORM
        A2 -->|"options"| BRAINSTORM
    end

    subgraph "Phase 3: Evaluate & Commit"
        BRAINSTORM --> EVAL[Score each option<br/>against both parties'<br/>interest maps]:::stage
        EVAL --> BEST{Pareto optimal<br/>option found?}:::decision
        BEST -->|"yes"| COMMIT[Both parties<br/>commit to terms]:::stage
        BEST -->|"no: expand"| BRAINSTORM
    end

    COMMIT --> O[Agreement:<br/>Terms + Interest<br/>Satisfaction Map]:::stage

    subgraph Details
        D1["Agents: N parties + 1 mediator"]:::stage
        D2["Key rule: Interests, not positions"]:::stage
        D3["Decision: Pareto optimality — no party worse off"]:::stage
        D4["Output: Agreement with interest satisfaction scores"]:::stage
    end

    classDef agent fill:#F39C12,stroke:#D68910,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```
