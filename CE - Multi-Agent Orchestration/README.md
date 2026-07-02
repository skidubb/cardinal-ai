# The Coordination Lab

**60 multi-agent coordination protocols, 74 AI agents, and an adaptive router — a research platform and production engine for strategic decision-making.**

Scott Ewalt | [Cardinal Element](https://cardinalelement.com) | 2026

---

## What This Is

A systematic research program and production platform that answers: *which coordination architecture works best for which kind of strategic problem?*

60 protocols drawn from eight coordination traditions are tested against 34 benchmark questions across 8 problem types. The platform includes a full web UI, PDF report generation, pipeline chaining, and an adaptive router (Cynefin-based) that selects the optimal protocol based on problem characteristics. Deployed on Railway with Postgres persistence and Langfuse observability.

## Quick Start

```bash
cd "CE - Multi-Agent Orchestration"
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run a protocol
python -m protocols.p06_triz.run -q "Should we expand into Europe?" -a ceo cfo cto

# Multi-round protocols
python -m protocols.p04_multi_round_debate.run -q "Should we expand?" -a ceo cfo cto --rounds 3

# All protocols accept: -q, -a, --thinking-model, --orchestration-model, --mode
# Multi-round protocols also accept: --rounds/-r

# Evaluation harness
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
```

## Problem Types

| # | Type | Core Challenge |
|---|------|----------------|
| 1 | **Integration** | Combine multiple valid perspectives into a coherent plan |
| 2 | **Adversarial** | Stress-test assumptions under competitive pressure |
| 3 | **Stakeholder Tension** | Satisfy competing parties with hard constraints |
| 4 | **Diagnostic** | Identify root cause of underperformance |
| 5 | **Exploration** | Generate novel options in open-ended space |
| 6 | **Prioritization** | Rank competing valid options defensibly |
| 7 | **Paradox/Wicked** | Sharpen irresolvable tensions for management |
| 8 | **Risk/Pre-Mortem** | Identify failure modes in an accepted plan |

## 60 Protocols

Twelve categories spanning meta-routing (P0a–c), single- and multi-agent baselines (P00–P01, P3–P5), Liberating Structures (P6–P15), intelligence analysis (P16–P18), game theory (P19–P21), org theory (P22–P23), systems thinking (P24–P25), design thinking (P26–P27), Wave 2 research — philosophy, military strategy, cognitive science (P28–P48), walk protocols (P49–P52), and decentralized coordination (P53–P57).

The canonical per-protocol taxonomy lives in [CLAUDE.md → Protocol Taxonomy](CLAUDE.md#protocol-taxonomy); each protocol's `capability.yaml` is the machine-readable source of truth.

## Architecture

```
CE - Multi-Agent Orchestration/
├── protocols/                    # 60 protocol implementations
│   ├── p{NN}_{name}/            #   Each: orchestrator.py, prompts.py, run.py
│   ├── agents.py                #   74-agent registry across 15 categories
│   ├── server_agent.py          #   Production agent (direct Anthropic API + tools)
│   ├── agent_provider.py        #   Builds agents per mode (production/research)
│   ├── llm.py                   #   LLM dispatch (ServerAgent → LiteLLM → SDK fallback)
│   ├── config.py                #   Model & runtime configuration
│   ├── cost_tracker.py          #   Token usage & cost tracking
│   ├── langfuse_tracing.py      #   @trace_protocol decorator
│   ├── persistence.py           #   Postgres run persistence
│   └── walk_shared/             #   Shared logic for Walk protocols (P49-P52)
├── api/                         # FastAPI backend
│   ├── server.py                #   App entry point
│   ├── runner.py                #   Protocol execution engine (SSE streaming)
│   ├── routers/                 #   REST endpoints (protocols, runs, agents, pipelines, teams)
│   ├── database.py              #   SQLModel + Postgres
│   ├── models.py                #   Run, RunStep, AgentOutput, Agent, Pipeline, Team
│   ├── tool_executor.py         #   Dispatches tool calls to Agent Builder handlers
│   └── templates/               #   PDF report templates (WeasyPrint)
├── ui/                          # React + TypeScript frontend
│   └── src/pages/               #   Dashboard, RunHistory, RunDetail, ProtocolLibrary,
│                                #   AgentRegistry, Pipelines, Teams, KnowledgeExplorer,
│                                #   ToolsHub, Settings
├── scripts/                     # Evaluation harness, batch runners
├── benchmark-questions.json     # 34 questions across 8 problem types
├── protocol-diagrams/           # Mermaid diagrams for all protocol families
├── smoke-tests/                 # Saved protocol outputs for regression
└── evaluations/                 # Eval results and analysis
```

### Key Components

**ServerAgent** — The production agent class. Direct `anthropic.AsyncAnthropic()` calls with native tool-use loop (max 15 iterations). Imports role prompts and 27 tool schemas from CE - Agent Builder. No subprocess spawning — works in Docker/Railway.

**Two model tiers** — `thinking_model` (Claude Opus) for agent reasoning and synthesis; `orchestration_model` (Claude Haiku) for mechanical steps like dedup, ranking, and classification.

**Agent registry** — 74 agents (60 core + 14 walk perspectives) across 15 categories: C-Suite executives, GTM leadership, revenue operations, customer success, finance, product, operations, technology, VC/investor personas, and behavioral coaches. Supports `@category` group syntax (e.g., `@executive`, `@gtm`).

**Pipeline chaining** — Multi-step protocol pipelines where each protocol's output feeds into the next. Checkpoint-based with resume support.

## Web UI & API

FastAPI backend + React frontend, deployed on Railway at `cardinal-ai-production.up.railway.app`.

- **SSE streaming** for live protocol execution progress
- **PDF reports** via WeasyPrint with branded templates
- **Pipeline builder** for multi-protocol chains
- **Agent management** with custom agent creation
- **Team management** for agent group presets
- **Knowledge explorer** for RAG context integration

### Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/protocols/run` | Stream protocol execution (SSE) |
| `POST` | `/api/protocols/run/with-context` | Run with file upload (RAG) |
| `POST` | `/api/pipelines/run` | Execute multi-step pipeline |
| `GET` | `/api/runs` | List all runs |
| `GET` | `/api/reports/{run_id}/pdf` | Download PDF report |
| `GET` | `/api/protocols` | Protocol manifest |
| `GET` | `/api/agents` | Agent registry |

## Observability

- **Langfuse tracing** — Every protocol run creates a trace with child spans for each LLM call. Deployed against Langfuse Cloud.
- **Postgres persistence** — Run metadata, results, agent outputs, and cost data persisted via async SQLAlchemy + asyncpg.
- **Cost tracking** — Per-run token usage and cost computed from model pricing.

Both layers degrade gracefully — tracing or DB failures never block protocol execution.

## Deployment

Multi-stage Dockerfile: Node build (React UI) → Python runtime with system deps (cairo, pango for WeasyPrint). Railway Postgres addon for DB. Healthcheck at `/api/health`.

## Key References

- **Reasoning Router** (2025) — Dynamic multi-strategy reasoning for robust problem solving
- **AgentiQL** (NeurIPS 2025) — Agent-inspired multi-expert architecture with learned routing
- **TAO Framework** — Tiered Adaptive Oversight for safety-critical routing
- **TRIZ Agents** (ICAART 2025) — Multi-agent LLM approach for TRIZ-based innovation
- **AgentCDM** (2025) — ACH-inspired structured reasoning for multi-agent decision-making

## License

Proprietary — Cardinal Element, 2026.
