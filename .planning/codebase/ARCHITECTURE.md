# CE-AGENTS Architecture

Purpose: Document the architectural patterns, layers, data flow, abstractions, and entry points of the CE-AGENTS monorepo.

---

## System Overview

CE-AGENTS is a monorepo for Cardinal Element's multi-agent AI platform. It implements a three-layer architecture:

1. **Agent Layer** (CE - Agent Builder) -- Build and configure AI agents with tools, memory, and MCP servers
2. **Orchestration Layer** (CE - Multi-Agent Orchestration) -- Run agents through 53 coordination protocols
3. **Evaluation Layer** (CE - Evals) -- Score agent/protocol outputs with blind multi-judge evaluation

A shared database layer (ce-db) provides persistence across all three, and n8n workflows provide external automation.

```
                    +-------------------+
                    |   React UI        |  <-- User-facing dashboard
                    | (Vite + TypeScript)|
                    +--------+----------+
                             | SSE/REST
                    +--------v----------+
                    |   FastAPI Server   |  <-- api/server.py
                    |  (api/runner.py)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+        +----------v---------+
    | Protocol           |        |  Evaluation        |
    | Orchestrators      |        |  (CE - Evals)      |
    | (53 protocols)     |        |  BlindJudge +      |
    |                    |        |  multi-model scoring|
    +--------+-----------+        +----------+---------+
             |                               |
    +--------v-----------+                   |
    | Agent Layer         |                  |
    | (CE - Agent Builder)|                  |
    | SdkAgent / BaseAgent|                  |
    +--------+------------+                  |
             |                               |
    +--------v-------------------------------v-----+
    |          ce-db (PostgreSQL + Alembic)         |
    |  runs | agent_outputs | eval_runs | agents   |
    +----------------------------------------------+
```

---

## Sub-Project Relationships

### Build Agents, Run Through Protocols

The fundamental design principle: **agents are built in Agent Builder, then orchestrated through protocols in Multi-Agent Orchestration.**

- Agent Builder defines `SdkAgent` -- a fully-equipped agent with Claude Agent SDK, MCP server access, Pinecone memory, and tool calling
- Multi-Agent Orchestration's `AgentBridge` wraps `SdkAgent` instances to be dict-compatible with protocol code
- Protocols call `agent.chat(prompt)` and receive responses from capable agents -- not bare LLM completions

### Dual Agent Mode

The system supports two operating modes controlled by `--mode` flag or `AGENT_MODE` env var:

| Mode | Agent Type | Tools | Memory | Use Case |
|------|-----------|-------|--------|----------|
| `production` | `SdkAgent` via `AgentBridge` | Yes (MCP servers) | Yes (Pinecone) | Real runs with full capabilities |
| `research` | Plain dicts `{"name", "system_prompt"}` | No | No | Fast iteration, testing, cost-efficient |

Resolution chain in `protocols/agents.py` -> `build_agents()`:
1. If `mode=production`: calls `build_production_agents()` in `agent_provider.py`
2. `agent_provider.py` adds `CE - Agent Builder/src` to `sys.path`, imports `SdkAgent`
3. Each agent key gets wrapped in `AgentBridge` for dict-compatible protocol access
4. If import fails, falls back to research mode for that agent

---

## Agent System Architecture

### Two Agent Backends (Agent Builder)

Located in `CE - Agent Builder/src/csuite/agents/`:

**BaseAgent** (`base.py`) -- Legacy backend using direct Anthropic API:
- Abstract base class; subclasses set `ROLE` and implement `get_system_prompt()`
- Agentic tool-use loop (up to 15 iterations)
- Session persistence (JSON files)
- DuckDB-backed memory, experience logging, preference tracking
- Cost tracking with per-query ceilings
- Retry with exponential backoff

**SdkAgent** (`sdk_agent.py`) -- Modern backend using Claude Agent SDK:
- Does NOT subclass BaseAgent -- independent, minimal interface
- Uses `claude_agent_sdk.query()` with per-role MCP server access
- Stateless (no session persistence)
- 80+ agents registered in `_ROLE_PROMPTS` dict
- MCP server config from `mcp_config.py` (Pinecone, Notion, SEC EDGAR, Pricing, GitHub Intel)

**Factory** (`factory.py`) -- Routes to backend based on `AGENT_BACKEND` setting:
```python
def create_agent(role, cost_tracker=None, **kwargs):
    if backend == "sdk" or role not in _LEGACY_CLASSES:
        return SdkAgent(role=role, cost_tracker=cost_tracker)
    return _LEGACY_CLASSES[role](cost_tracker=cost_tracker, **kwargs)
```

### Agent Registry (Multi-Agent Orchestration)

Located in `CE - Multi-Agent Orchestration/protocols/agents.py`:

- 56+ agents across 15 categories in `BUILTIN_AGENTS` flat dict
- Categories: executive, ceo-team, cfo-team, cmo-team, coo-team, cpo-team, cto-team, gtm-leadership, gtm-sales, gtm-marketing, gtm-partners, gtm-success, gtm-ops, external, walk
- Supports `@category` group syntax (e.g., `@executive` expands to all 7 C-suite agents)
- External agents (vc-app-investor, vc-infra-investor) specify non-Anthropic models (GPT-5, Gemini)
- Meta agents (synthesizer, judge) are infrastructure-only -- not user-selectable

---

## Protocol Orchestration Pattern

### Standard Protocol Structure

Every protocol lives in `protocols/p{NN}_{name}/` with:

| File | Purpose |
|------|---------|
| `__init__.py` | Exports orchestrator class and result dataclass |
| `orchestrator.py` | Async class with `run(question) -> *Result` |
| `prompts.py` | All LLM prompt templates as string constants |
| `run.py` | CLI entry point with argparse |
| `protocol_def.py` | (some protocols) Protocol metadata for manifest |

### Two-Tier Model Strategy

Defined in `protocols/config.py`:

- **Thinking Model** (`claude-opus-4-6`) -- Agent reasoning, synthesis, creative stages
- **Orchestration Model** (`claude-haiku-4-5-20251001`) -- Mechanical steps (dedup, ranking, extraction)
- **Balanced Model** (`claude-sonnet-4-6`) -- Mid-tier analytical reasoning

**Cognitive Depth Tiers** (CogRouter-inspired):
- L1 (Haiku): Pattern match -- dedup, classify, extract, parse
- L2 (Haiku): Rule-based -- score, rank, filter, vote
- L3 (Sonnet): Analytical -- assess, compare, analyze, evaluate
- L4 (Opus): Creative/Strategic -- synthesize, ideate, debate, reframe

### LLM Dispatch (`protocols/llm.py`)

Two dispatch paths:

1. **`agent_complete()`** -- For agent-identity calls:
   - If agent has `.chat()` method (production SdkAgent): calls it directly
   - If agent has `"model"` field: routes through LiteLLM (supports OpenAI, Gemini, etc.)
   - Otherwise: uses Anthropic SDK with orchestrator's `thinking_model`
   - Includes agentic tool loop via `api/tool_executor.py`

2. **`llm_complete()`** -- For orchestration-level calls:
   - Direct Anthropic SDK wrapper
   - Used for dedup, ranking, scoring -- no agent identity
   - Automatic retry (3 attempts with 1s/2s/4s backoff + jitter)

Both record usage to `ProtocolCostTracker` and emit Langfuse generation spans.

### Protocol Taxonomy (53 protocols)

| Category | Protocols | Pattern |
|----------|-----------|---------|
| Meta (P0a-c) | Reasoning Router, Skip Gate, Tiered Escalation | Route/gate before execution |
| Baselines (P3-P5) | Parallel Synthesis, Multi-Round Debate, Constraint Negotiation | Fundamental patterns |
| Liberating Structures (P6-P15) | TRIZ, Wicked Questions, Min Specs, Troika, etc. | Meeting facilitation adapted |
| Intelligence Analysis (P16-P18) | ACH, Red/Blue/White, Delphi | Structured analytic techniques |
| Game Theory (P19-P21) | Vickrey Auction, Borda Count, Interests Negotiation | Mechanism design |
| Org Theory (P22-P23) | Sequential Pipeline, Cynefin Probe | Organizational patterns |
| Systems Thinking (P24-P25) | Causal Loop Mapping, System Archetype Detection | Feedback loop analysis |
| Design Thinking (P26-P27) | Crazy Eights, Affinity Mapping | Creative ideation |
| Wave 2 Research (P28-P48) | Six Hats, PMI, Tetlock, Klein, Popper, OODA, etc. | Advanced reasoning |
| Walk Protocols (P49-P52) | Walk Base, Tournament, Wildcard, Drift-Return | LLM on a Walk family |

### Example: TRIZ Protocol Flow (P6)

```
Question
  |
  v
Stage 2: Parallel failure generation (agents in parallel via asyncio.gather)
  |
  v
Stage 3: Dedup & categorize (orchestration model)
  |
  v
Stage 4: Invert failures -> solutions (orchestration model)
  |
  v
Stage 5: Rank by severity x likelihood (orchestration model)
  |
  v
Stage 6: Synthesize final briefing (thinking model via SynthesisEngine)
  |
  v
TRIZResult { failure_modes, solutions, synthesis, agent_contributions }
```

---

## API and UI Layer

### FastAPI Server (`api/server.py`)

Entry point: `api/server.py` -- FastAPI with CORS for `localhost:5173/5174`.

Routers:
- `api/routers/protocols.py` -- Protocol listing, execution
- `api/routers/runs.py` -- Run history, SSE streaming
- `api/routers/agents.py` -- Agent CRUD, tools registry
- `api/routers/teams.py` -- Team management
- `api/routers/pipelines.py` -- Multi-protocol pipeline execution
- `api/routers/knowledge.py` -- Knowledge base operations
- `api/routers/integrations.py` -- External service integrations

### API Runner (`api/runner.py`)

The core execution engine for API-triggered runs:

1. Dynamically discovers orchestrator classes by scanning `protocols/p*/orchestrator.py`
2. Resolves agents from DB (rich, with frameworks/deliverables) or falls back to registry (thin)
3. Sets up `ProtocolCostTracker`, event queue for SSE, and tool controls
4. Runs protocol as async task, drains event queue for live SSE streaming
5. After completion: runs `QualityJudge`, persists to SQLite + Postgres, scores Langfuse trace
6. Pipeline mode: chains protocols sequentially, passing outputs forward via `{prev_output}` template

### React UI (`ui/`)

Vite + TypeScript + React frontend at `ui/src/`:

Pages: Dashboard, ProtocolLibrary, RunView, RunHistory, AgentRegistry, AgentEditor, Pipelines, Teams, KnowledgeExplorer, ToolsHub, Settings, ProtocolDiagram

---

## Observability Stack

### Langfuse Tracing (`protocols/langfuse_tracing.py`)

- Every orchestrator's `run()` is decorated with `@trace_protocol("p{NN}_name")`
- Creates root span per protocol run
- Child spans for each stage (failure_generation, dedup, inversion, etc.)
- Generation spans for each LLM call via `record_generation()`
- Quality scores attached to traces (completeness, consistency, actionability)
- Cost scores attached for unified cost+quality dashboards
- Uses Langfuse Cloud (us.cloud.langfuse.com)

### Postgres Persistence (`protocols/persistence.py`)

- Every CLI `run.py` and API run calls `persist_run()`
- Writes `Run` and `AgentOutput` rows to Postgres via ce-db
- Explicit `PersistOutcome` with telemetry degradation warnings
- Gracefully degrades if ce-db is unavailable

### Cost Tracking (`protocols/cost_tracker.py`)

- `ProtocolCostTracker` tracks per-call costs by model and agent
- Supports Anthropic pricing tiers (Opus/Sonnet/Haiku) with cached token discounts
- Summaries available as `by_model` and `by_agent` breakdowns
- API runner records cost as Langfuse score for dashboard filtering

---

## Evaluation Pipeline (CE - Evals)

### Core Architecture

Library-only (no CLI). Three-stage pipeline:

1. **Candidate Execution**: `EvalRunner.run()` takes candidate callables, runs each on a question
2. **Blind Judging**: `BlindJudge.evaluate()` anonymizes outputs, scores with rubric across multiple judge models
3. **Report Generation**: `report/markdown.py` produces evaluation reports

### Key Components

- **Rubric** (`core/rubric.py`): YAML-defined scoring dimensions (1-5 scale), builds judge system prompts
- **BlindJudge** (`core/judge.py`): Anonymizes candidates, evaluates with multiple models in parallel, aggregates via Borda count
- **Judge Backends** (`core/judge_backends.py`): Claude, GPT-4, Gemini -- selectable per evaluation
- **Blind Protocol** (`protocols/blind.py`): Anonymization (Response A/B/C) and metadata stripping
- **EvalRunner** (`core/runner.py`): Orchestrates candidates x questions, persists to Postgres

### Data Flow

```
Candidate Functions  -->  EvalRunner.run()
                              |
                    Execute each candidate on question
                              |
                    Collect CandidateResult (output, cost, duration)
                              |
                    BlindJudge.evaluate()
                         |         |         |
                    Claude      GPT-4     Gemini    (parallel)
                         |         |         |
                    _aggregate_results() -- mean scores, Borda ranking
                              |
                    EvalSuite { candidates, judgment, per_judge_results }
                              |
                    Persist to Postgres (eval_runs, eval_samples, eval_regressions)
```

---

## Shared Database Layer (ce-db)

### Schema

SQLAlchemy declarative models with Alembic migrations:

**Core** (`models/core.py`):
- `Agent` -- agent registry with key, system_prompt, model, tools_json, mcp_servers_json

**Runs** (`models/runs.py`):
- `Run` -- protocol execution record (protocol_key, question, agent_keys, status, cost, result_json, langfuse_trace_id)
- `AgentOutput` -- per-agent output within a run (agent_key, round_number, output_text, cost_usd, tokens)

**Evals** (`models/evals.py`):
- `EvalRun` -- evaluation execution (rubric_name, judge_backend, aggregate_score, scores_json)
- `EvalSample` -- per-candidate measurement (score, variance, is_correct, cost, tokens)
- `EvalRegression` -- precomputed quality deltas against baseline (quality_delta, cost_per_correct_delta, status)

### Session Management

- Async SQLAlchemy with asyncpg driver
- `get_session()` context manager for transactions
- Default: `postgresql+asyncpg://ce:ce_local@localhost:5432/ce_platform`

---

## Infrastructure

### Docker Compose

- **Postgres 16**: Primary data store (ce_platform database)
- **Metabase**: Analytics dashboard on port 3001
- **Langfuse**: Uses cloud (us.cloud.langfuse.com); self-hosted config commented out

### External Services

| Service | Purpose | Required |
|---------|---------|----------|
| Anthropic API | Primary LLM provider | Yes |
| LiteLLM | Multi-provider routing (OpenAI, Gemini, etc.) | For non-Anthropic agents |
| Pinecone | Knowledge base + agent memory | Optional (degrades gracefully) |
| Notion | Integration for agent tools | Optional |
| Langfuse Cloud | Observability/tracing | Optional (no-op if unavailable) |
| PostgreSQL | Run/eval persistence | Optional (no-op if unavailable) |

---

## Key Design Patterns

### Async Everywhere
All agent calls, protocol stages, and API handlers use `async/await`. Parallel agent queries use `asyncio.gather()` with `return_exceptions=True` for partial failure tolerance.

### Graceful Degradation
Every external dependency (Pinecone, Postgres, Langfuse, ce-db) wraps in try/except with fallback behavior. Nothing crashes if an optional service is unavailable.

### Context Variables for Cross-Cutting Concerns
`protocols/llm.py` uses `contextvars.ContextVar` to propagate:
- `_cost_tracker`: Active cost tracker instance
- `_event_queue`: SSE event queue for live tool visibility
- `_no_tools`: Protocol-level tool disable flag

### Protocol Result Dataclasses
Each protocol defines its own result type (e.g., `TRIZResult`, `DebateResult`) with typed fields. The `RunEnvelope` standardizes persistence across all protocols.

### AgentBridge Adapter Pattern
`AgentBridge` in `agent_provider.py` wraps `SdkAgent` to provide both:
- Dict-style access (`agent["name"]`, `agent["system_prompt"]`) for protocol compatibility
- `.chat()` method that `agent_complete()` detects for production routing
