# Cardinal Element -- C-Suite Agent Architecture

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        UI["Streamlit Demo App<br/>(demo/app.py)"]
        CLI["CLI: csuite command<br/>(src/csuite/main.py)"]
    end

    subgraph "Agent Layer"
        BASE["BaseAgent ABC<br/>(agents/base.py)"]
        CFO["CFO Agent<br/>Temperature: 0.5"]
        CTO["CTO Agent<br/>Temperature: 0.6"]
        CMO["CMO Agent<br/>Temperature: 0.8"]
        COO["COO Agent<br/>Temperature: 0.6"]
        ORCH["Orchestrator<br/>Parallel Query + Synthesis<br/>(orchestrator.py)"]
    end

    subgraph "Data Enrichment Layer (Free APIs)"
        SEC["SEC EDGAR API<br/>Company Financials<br/>Rate: 10 req/sec"]
        CENSUS["Census Bureau API<br/>Industry Benchmarks<br/>Rate: 500/day"]
        BLS["BLS API<br/>Labor Market Data<br/>Rate: 25/day"]
        GH["GitHub API<br/>Tech Stack Analysis<br/>Rate: 60/hr"]
    end

    subgraph "Intelligence Layer"
        CLAUDE["Claude API<br/>Opus 4.6 (strategy)<br/>Sonnet 4.5 (demo)<br/>Haiku 4.5 (extraction)"]
        ICP["ICP Scoring Engine<br/>Deterministic (no LLM)<br/>B2B / $5-40M / 20-150 emp"]
        COST["Cost Tracker (D10)<br/>Per-query cost logging<br/>Alert thresholds"]
    end

    subgraph "Resilience Layer (Sprint 2)"
        RETRY["Retry + Backoff<br/>3 retries, exponential"]
        CACHE["TTL Cache<br/>5min API / 1hr demo"]
        CB["Circuit Breaker<br/>5 failures = open"]
        DEGRADE["Graceful Degradation<br/>Partial results, not errors"]
    end

    subgraph "Persistence Layer"
        SESSIONS["Session Manager<br/>JSON files per agent"]
        REPORTS["Report Generator<br/>Markdown + PDF"]
    end

    UI --> ORCH
    CLI --> ORCH
    ORCH --> CFO & CTO & CMO & COO
    CFO & CTO & CMO & COO --> BASE
    BASE --> CLAUDE
    BASE --> COST
    BASE --> SESSIONS

    UI --> SEC & GH
    UI --> ICP

    SEC & CENSUS & BLS & GH --> RETRY
    RETRY --> CACHE
    CACHE --> CB
    CB --> DEGRADE

    style UI fill:#D4AF37,color:#0B1E3F,stroke:#0B1E3F
    style CLI fill:#D4AF37,color:#0B1E3F,stroke:#0B1E3F
    style CLAUDE fill:#0B1E3F,color:#fff,stroke:#D4AF37
    style ICP fill:#10B981,color:#fff,stroke:#0B1E3F
    style COST fill:#3B82F6,color:#fff,stroke:#0B1E3F
    style RETRY fill:#F59E0B,color:#0B1E3F,stroke:#0B1E3F
    style CACHE fill:#F59E0B,color:#0B1E3F,stroke:#0B1E3F
    style CB fill:#F59E0B,color:#0B1E3F,stroke:#0B1E3F
    style DEGRADE fill:#F59E0B,color:#0B1E3F,stroke:#0B1E3F
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent model | Claude Opus 4.6 | Strategic reasoning requires frontier model capability |
| Demo model | Claude Sonnet 4.5 | Faster response for live demos; acceptable quality tradeoff |
| Data APIs | 4 free government APIs | Replace $500+/mo in paid services (BuiltWith, Crunchbase, etc.) |
| ICP scoring | Deterministic (no LLM) | Consistent, explainable, instant -- no API cost per score |
| Session persistence | JSON files | Simple, portable, no database dependency. Upgrade to DB in Sprint 3 |
| Cost tracking | Per-query logging | Directive D10 compliance. Enables margin analysis on every engagement |
| Deployment | Streamlit Community Cloud | Free tier, auto-deploy from GitHub, adequate for demo stage |

## API Cost Model

| Tier | Model | Input ($/MTok) | Output ($/MTok) | Use Case |
|------|-------|----------------|-----------------|----------|
| Executive | Opus 4.6 | $5.00 | $25.00 | Strategy, synthesis, board-level analysis |
| Specialist | Sonnet 4.5 | $3.00 | $15.00 | Research, content, demo responses |
| Extraction | Haiku 4.5 | $1.00 | $5.00 | Data extraction, classification |

## Data Flow: Prospect Research

```
1. User enters ticker (e.g., "EPAM")
   |
2. Check pre-cached demo data (instant, 0 API calls)
   |-- if cached: return immediately
   |-- if not: continue to step 3
   |
3. SEC EDGAR: Company Info + Financials
   |-- Rate limited: 10 req/sec
   |-- Retry: 3x with exponential backoff
   |-- Cache: 5min TTL
   |
4. ICP Scoring Engine (deterministic)
   |-- Revenue fit: $5-40M range
   |-- Employee fit: 20-150 range
   |-- Industry fit: B2B operator keywords
   |
5. Display results in Streamlit
   |
6. User asks C-Suite agent a question
   |
7. Claude API call (Sonnet for demo)
   |-- Cost tracked per Directive D10
   |-- Response rendered in markdown
```

---

*Architecture document -- CTO Sprint 2 Deliverable 5*
*Cardinal Element -- February 2026*
