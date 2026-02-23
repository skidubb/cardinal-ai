# Design Thinking (P26–P27)

## P26: Crazy Eights

**8 ideas under extreme time/resource constraints — forces radical divergence.**

### Summary Flow

```mermaid
graph LR
    AG([Agents]):::agent -->|"8 rapid ideas<br/>each"| COLLECT[Collect All]:::stage
    COLLECT -->|"best ideas"| O[Output]:::stage
    classDef agent fill:#E91E63,stroke:#C2185B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"design challenge"| CONSTRAIN[Set Extreme Constraints:<br/>8 ideas, minimal tokens,<br/>no self-editing]:::stage

    CONSTRAIN --> A1([Agent 1]):::agent
    CONSTRAIN --> A2([Agent 2]):::agent
    CONSTRAIN --> AN([Agent N]):::agent

    subgraph "Phase 1: Rapid Generation"
        A1 -->|"8 raw ideas"| POOL[Idea Pool<br/>— 8 x N ideas total]:::stage
        A2 -->|"8 raw ideas"| POOL
        AN -->|"8 raw ideas"| POOL
    end

    subgraph "Phase 2: Cluster & Select"
        POOL --> CLUSTER[Cluster Similar<br/>Ideas by Theme]:::stage
        CLUSTER --> DOT{Dot Voting:<br/>Each agent gets<br/>3 votes}:::decision
        DOT --> TOP[Top Voted Ideas]:::stage
    end

    subgraph "Phase 3: Develop"
        TOP --> DEVELOP[Develop Top 3-5<br/>Ideas into Concepts]:::stage
        DEVELOP --> O[Concept Sketches<br/>with Rationale]:::stage
    end

    subgraph Details
        D1["Agents: N generators + 1 facilitator"]:::stage
        D2["Constraint: 8 ideas each, brevity enforced"]:::stage
        D3["Selection: Dot voting (3 votes per agent)"]:::stage
        D4["Output: Top concepts developed from rapid ideas"]:::stage
    end

    classDef agent fill:#E91E63,stroke:#C2185B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```

---

## P27: Affinity Mapping

**Generate items → embedding-based clustering → theme labeling.**

### Summary Flow

```mermaid
graph LR
    AG([Agents]):::agent -->|"items"| EMB[Embedding<br/>Cluster]:::stage
    EMB -->|"themes"| LABEL[Label<br/>Themes]:::stage
    LABEL --> O[Output]:::stage
    classDef agent fill:#E91E63,stroke:#C2185B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
```

### Detailed Mechanics

```mermaid
graph TB
    U([User]):::agent -->|"topic / data"| PH1[Phase 1: Generate<br/>Individual Items]:::stage

    PH1 --> A1([Agent 1]):::agent
    PH1 --> A2([Agent 2]):::agent
    PH1 --> AN([Agent N]):::agent

    A1 -->|"items / observations"| POOL[Item Pool<br/>— all items]:::stage
    A2 -->|"items"| POOL
    AN -->|"items"| POOL

    POOL --> PH2[Phase 2: Embed<br/>& Cluster]:::stage
    PH2 --> EMBED[Generate Embeddings<br/>for each item]:::stage
    EMBED --> CLUSTER[Cluster: k-means or<br/>hierarchical on<br/>embedding space]:::stage

    CLUSTER --> PH3[Phase 3: Label<br/>& Organize]:::stage

    PH3 --> LABEL([Labeler Agent]):::agent
    LABEL --> THEMES[Generate Theme Name<br/>per Cluster + Summary]:::stage

    THEMES --> REVIEW{Review: Clusters<br/>coherent? Items<br/>misplaced?}:::decision
    REVIEW -->|"clean"| HIERARCHY[Build Theme<br/>Hierarchy]:::stage
    REVIEW -->|"adjust"| CLUSTER

    HIERARCHY --> O[Affinity Map:<br/>Themes → Sub-themes<br/>→ Items]:::stage

    subgraph Details
        D1["Agents: N generators + 1 labeler"]:::stage
        D2["Clustering: Embedding-based (not keyword)"]:::stage
        D3["Validation: Coherence check on clusters"]:::stage
        D4["Output: Hierarchical theme map with all items placed"]:::stage
    end

    classDef agent fill:#E91E63,stroke:#C2185B,color:#fff
    classDef stage fill:#E8E8E8,stroke:#999,color:#333
    classDef decision fill:#F5A623,stroke:#D48A1A,color:#fff
```
