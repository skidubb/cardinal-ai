# cardinal-ai

Monorepo for **Cardinal Element's** agentic AI platform — multi-agent systems, coordination protocols, evaluation frameworks, and automation workflows.

Cardinal Element is an AI-native growth architecture consultancy. This repo powers the core product: **build specialized AI agents, orchestrate them through research-backed coordination protocols, and evaluate the quality of their outputs.**

## Architecture

```
                     +-------------------+
                     |   React UI        |  Dashboard (Vite + TypeScript)
                     | localhost:5173    |
                     +--------+----------+
                              | SSE / REST
                     +--------v----------+
                     |   FastAPI Server   |  api/server.py
                     |  (api/runner.py)   |
                     +--------+----------+
                              |
               +--------------+--------------+
               |                             |
     +---------v---------+        +----------v---------+
     | Protocol            |        |  Evaluation        |
     | Orchestrators       |        |  (CE - Evals)      |
     | (53 protocols)      |        |  Blind multi-judge  |
     +--------+-----------+        +----------+---------+
              |                               |
     +--------v-----------+                   |
     | Agent Layer         |                  |
     | (CE - Agent Builder)|                  |
     | SdkAgent + tools    |                  |
     +--------+------------+                  |
              |                               |
     +--------v-------------------------------v-----+
     |         ce-db (PostgreSQL + Alembic)          |
     |  runs | agent_outputs | eval_runs | agents    |
     +----------------------------------------------+
```

### Three-Layer Design

1. **Agent Layer** (CE - Agent Builder) -- Build and configure AI agents with Claude Agent SDK, MCP server access, Pinecone memory, and tool calling
2. **Orchestration Layer** (CE - Multi-Agent Orchestration) -- Run agents through 53 coordination protocols with a React UI, FastAPI backend, and SSE streaming
3. **Evaluation Layer** (CE - Evals) -- Score agent/protocol outputs with blind multi-judge evaluation (Claude, GPT-4, Gemini)

### Dual Agent Mode

| Mode | Agent Type | Tools | Memory | Use Case |
|------|-----------|-------|--------|----------|
| `production` | `SdkAgent` via `AgentBridge` | Yes (MCP servers) | Yes (Pinecone) | Real runs with full capabilities |
| `research` | Plain dicts `{"name", "system_prompt"}` | No | No | Fast iteration, testing, cost-efficient |

Set via `--mode production` (default) or `--mode research` / `AGENT_MODE=research`.

### Model Strategy

| Tier | Model | Purpose |
|------|-------|---------|
| L4 (Thinking) | `claude-opus-4-6` | Agent reasoning, synthesis, creative stages |
| L3 (Balanced) | `claude-sonnet-4-6` | Structured analytical reasoning |
| L1-L2 (Orchestration) | `claude-haiku-4-5-20251001` | Mechanical steps (dedup, ranking, extraction) |

Non-Anthropic models (GPT, Gemini) supported via LiteLLM routing for external agents.

## Projects

```
CE - AGENTS/
├── CE - Agent Builder/               # Agent factory -- SdkAgent + BaseAgent backends
├── CE - Multi-Agent Orchestration/    # 53 protocols + FastAPI + React UI
│   ├── api/                          #   FastAPI server, runner, routers
│   ├── protocols/                    #   p00a-p52 protocol modules
│   └── ui/                           #   React dashboard (Vite + TypeScript)
├── CE - Evals/                       # Blind multi-judge evaluation framework
├── ce-db/                            # Shared PostgreSQL schema + Alembic migrations
├── ce-shared/                        # Cross-project shared utilities
├── content/                          # Blog posts, LinkedIn updates, newsletters
├── db-init/                          # SQL init scripts for Postgres + DuckDB analytics
├── Multi-Agent Research/             # Academic papers and research documents
├── n8n Workflows/                    # n8n automation workflow JSON exports
├── Scripts/                          # Utility scripts (Notion sync, n8n helpers)
└── Shared/                           # Legacy shared resources
```

### CE - Agent Builder

The agent factory. Two backends:

- **SdkAgent** (modern) -- Claude Agent SDK with per-role MCP server access (Pinecone, Notion, SEC EDGAR, GitHub Intel). 80+ agents registered. Stateless.
- **BaseAgent** (legacy) -- Direct Anthropic API with agentic tool-use loop, session persistence, DuckDB memory, cost tracking.

Factory routes to backend based on `AGENT_BACKEND` setting. Agents expose `async chat(message) -> str`.

```bash
cd "CE - Agent Builder"
pip install -e ".[dev]"

csuite ceo "What's our competitive position?"
csuite synthesize "Should we expand?" -a cfo cto cmo
csuite debate "Build vs buy?" -a ceo cfo cto -r 3
csuite audit "SaaS startup" --revenue "$12M" --employees 45
```

### CE - Multi-Agent Orchestration

53 coordination protocols across 10 categories, plus a full-stack web UI.

**Protocol categories:**
- **Meta (P0a-c):** Reasoning Router, Skip Gate, Tiered Escalation
- **Baselines (P3-P5):** Parallel Synthesis, Multi-Round Debate, Constraint Negotiation
- **Liberating Structures (P6-P15):** TRIZ, Wicked Questions, Min Specs, Troika, HSR, DAD, 25/10, Ecocycle, 1-2-4-All, What/So What/Now What
- **Intelligence Analysis (P16-P18):** ACH, Red/Blue/White Team, Delphi Method
- **Game Theory (P19-P21):** Vickrey Auction, Borda Count, Interests-Based Negotiation
- **Org Theory (P22-P23):** Sequential Pipeline, Cynefin Probe-Sense-Respond
- **Systems Thinking (P24-P25):** Causal Loop Mapping, System Archetype Detection
- **Design Thinking (P26-P27):** Crazy Eights, Affinity Mapping
- **Wave 2 Research (P28-P48):** Six Hats, PMI, Tetlock Forecasting, Klein Pre-Mortem, Popper Falsification, Boyd OODA, and 15 more
- **Walk Protocols (P49-P52):** LLM on a Walk family (Tournament, Wildcard, Drift-Return)

**Agent registry:** 56+ agents across 15 categories with `@category` group syntax (e.g., `@executive` expands to all C-suite agents).

```bash
cd "CE - Multi-Agent Orchestration"
pip install -r requirements.txt

# Run a protocol
python -m protocols.p06_triz.run -q "Should we expand into Europe?" -a ceo cfo cto
python -m protocols.p04_multi_round_debate.run -q "Build vs buy?" -a ceo cfo cto --rounds 3

# Start the API + UI
cd api && uvicorn server:app --reload    # FastAPI on :8000
cd ui && npm run dev                      # React on :5173

# Evaluation harness
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
```

### CE - Evals

Library-only evaluation framework. Three-stage pipeline:

1. **Execute** candidates on benchmark questions
2. **Blind judge** with anonymized outputs across multiple models (Claude, GPT-4, Gemini)
3. **Aggregate** via Borda count ranking with per-dimension rubric scores

### ce-db

Shared database layer. PostgreSQL + Alembic migrations. Tables: `runs`, `agent_outputs`, `eval_runs`, `eval_samples`, `eval_regressions`, `agents`.

## Observability

- **Langfuse tracing** -- Every protocol run creates a trace with child spans per stage and generation. Quality + cost scores attached. Uses Langfuse Cloud.
- **Postgres persistence** -- All runs (CLI and API) persist results, costs, and Langfuse trace IDs.
- **Cost tracking** -- Per-call costs by model and agent with Anthropic pricing tiers and cached token discounts.

## Setup

Each project has its own virtual environment. At minimum, each needs `ANTHROPIC_API_KEY` in `.env`.

```bash
# Agent Builder
cd "CE - Agent Builder" && python -m venv venv && source venv/bin/activate && pip install -e ".[dev]"

# Multi-Agent Orchestration
cd "CE - Multi-Agent Orchestration" && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Evals
cd "CE - Evals" && python -m venv venv && source venv/bin/activate && pip install -e .

# Database (optional)
docker-compose up -d postgres
```

Optional integrations (all degrade gracefully): Pinecone, Notion, Langfuse, LiteLLM (for non-Anthropic models).

## Previous Repos

This monorepo consolidates:
- [ce-c-suite](https://github.com/skidubb/ce-c-suite) -> `CE - Agent Builder/`
- [coordination-lab](https://github.com/skidubb/coordination-lab) -> `CE - Multi-Agent Orchestration/`
- [CE-Evals](https://github.com/skidubb/CE-Evals) -> `CE - Evals/`

## License

Proprietary -- Cardinal Element, LLC.
