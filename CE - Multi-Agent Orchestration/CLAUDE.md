# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The **Coordination Lab** is Cardinal Element's multi-agent research program and production platform. It contains 53 implemented coordination protocols (P0a-c, P3-P52) plus a shared 56-agent registry, 34 benchmark questions across 8 problem types, a FastAPI web UI with React frontend, and PDF report generation. Deployed on Railway at `cardinal-ai-production.up.railway.app`. The goal is to empirically validate these protocols across problem types, then build an adaptive router that selects the optimal protocol for any strategic question.

## Running Protocols

Every protocol is a standalone Python module. Only dependency: `anthropic` (see `requirements.txt`).

> **Note:** All CLI runs now persist results to Postgres and create Langfuse traces automatically (best-effort — silently no-ops if unavailable). API-triggered runs (via `api/runner.py`) additionally persist cost tracking, agent outputs, and error details.

```bash
# Run any protocol
python -m protocols.p06_triz.run -q "Should we expand into Europe?" -a ceo cfo cto
python -m protocols.p04_multi_round_debate.run -q "Should we expand?" -a ceo cfo cto --rounds 3
python -m protocols.p05_constraint_negotiation.run -q "Should we expand?" -a ceo cfo cto --rounds 2

# All protocols accept: --question/-q, --agents/-a, --agent-config, --thinking-model, --orchestration-model
# Multi-round protocols (P4, P5, P17, P18, etc.) also accept: --rounds/-r

# Run evaluation harness against benchmark questions
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto --dry-run
```

## Protocol Architecture (the pattern every protocol follows)

Each protocol lives in `protocols/p{NN}_{name}/` with these files:

| File | Purpose |
|------|---------|
| `__init__.py` | Exports the orchestrator class and result dataclass |
| `orchestrator.py` | The core logic: an async class with `run(question) -> *Result` |
| `prompts.py` | All LLM prompt templates as string constants |
| `run.py` | CLI entry point with argparse, `BUILTIN_AGENTS` dict, `print_result()` |
| `constraints.py` | Only in P5 — self-contained constraint extraction |

**Agent contract**:

> **Protocols orchestrate agents via `ServerAgent`** — direct Anthropic API calls with native tool-use.
>
> Each agent key (e.g., `ceo`, `cfo`, `cto`) resolves to a `ServerAgent` instance with: rich system prompt (from Agent Builder's `_ROLE_PROMPTS`), per-role tool schemas (from `ROLE_TOOL_MAP` → `ALL_TOOL_SCHEMAS`), and an agentic tool loop (max 15 iterations). The orchestrator calls `agent.chat(prompt)` and gets back a response from a capable, tool-using agent.
>
> This is the product: **define agents in Agent Builder (prompts + tools), run them through protocols in Orchestration.**
>
> Thin dicts `{"name": str, "system_prompt": str}` are the research/fallback mode — used via `--mode research` / `AGENT_MODE=research`.

**ServerAgent** (`protocols/server_agent.py`): Production agent class. Uses `anthropic.AsyncAnthropic().messages.create()` with tool schemas resolved from Agent Builder. No subprocess spawning — works in Docker/Railway. Imports: `_ROLE_PROMPTS` (70+ roles), `ALL_TOOL_SCHEMAS` (26 tools), `ROLE_TOOL_MAP` (40+ roles). Tool execution via `api/tool_executor.py`. Memory (Pinecone) and learning (DuckDB) degrade gracefully.

**Agent modes**: Production mode (default) builds `ServerAgent` instances via `build_production_agents()` in `protocols/agent_provider.py`. Research mode (`--mode research` or `AGENT_MODE=research` env var) uses lightweight dicts without tools.

**LLM dispatch** (`protocols/llm.py:agent_complete()`): Three paths — (1) `agent.chat()` exists → ServerAgent direct API, (2) `agent["model"]` set → LiteLLM, (3) plain dict → Anthropic SDK fallback with tool loop. Path 1 is production; Path 3 is the fallback.

**Model strategy**: Two model tiers passed to orchestrators:
- `thinking_model` (default: `claude-opus-4-7`) — for agent reasoning, synthesis, creative stages
- `orchestration_model` (default: `claude-haiku-4-5-20251001`) — for mechanical stages (dedup, ranking, extraction, classification)
- Agents support model override via `--agent-model` flag (routes through LiteLLM for non-Anthropic models like `gemini/gemini-3.1-pro-preview`)

**Async throughout**: All orchestrators use `anthropic.AsyncAnthropic()` and `asyncio.gather()` for parallel agent queries. CLIs wrap with `asyncio.run()`.

**Result pattern**: Each protocol defines dataclasses for its output (e.g., `TRIZResult`, `DebateResult`). Raw results are persisted as JSON to `smoke-tests/{pid}_raw_result.json` by the batch runner. Synthesis reports (markdown) are generated separately via Opus.

## Key Documents

- `The Coordination Lab *.md` — Master research spec: problem type taxonomy, protocols, evaluation rubrics, benchmark questions
- `benchmark-questions.json` — 34 structured benchmark questions across 8 problem types (referenced by `scripts/evaluate.py`)
- `protocols/agents.py` — Shared registry of 56 agents across 14 categories (supports `@category` group syntax)
- `protocol-diagrams/` — Mermaid diagrams for protocols (summary flows + detailed mechanics)
- `smoke-tests/` — Saved outputs from protocol runs for regression reference

## Protocol Taxonomy

- **P0a-P0c**: Meta-Protocols — Reasoning Router, Skip Gate, Tiered Escalation
- **P3-P5**: Baselines — Parallel Synthesis, Multi-Round Debate, Constraint Negotiation
- **P6-P15**: Liberating Structures — TRIZ, Wicked Questions, Min Specs, Troika, HSR, DAD, 25/10, Ecocycle, 1-2-4-All, What/So What/Now What
- **P16-P18**: Intelligence Analysis — ACH, Red/Blue/White Team, Delphi Method
- **P19-P21**: Game Theory — Vickrey Auction, Borda Count, Interests-Based Negotiation
- **P22-P23**: Org Theory — Sequential Pipeline, Cynefin Probe-Sense-Respond
- **P24-P25**: Systems Thinking — Causal Loop Mapping, System Archetype Detection
- **P26-P27**: Design Thinking — Crazy Eights, Affinity Mapping
- **P28-P52**: Wave 2 Research — Six Hats, PMI, Llull, Wittgenstein, Tetlock, Evaporation Cloud, CRT, Satisficing, Peirce, Hegel, Klein, Popper, Boyd OODA, Duke, Aristotle, Leibniz, Kant, Whitehead, Incubation, Polya, Black Swan, Walk Base, Tournament Walk, Wildcard Walk, Drift Return Walk

P1 (Single Agent) and P2 (Single + Context) are trivial single-call patterns with no orchestrator — they live in the C-Suite codebase only.

## Web UI & API

FastAPI backend (`api/`) + React/TypeScript frontend (`ui/`). Deployed on Railway.

### Key API Endpoints
- `POST /api/protocols/run` — Stream protocol execution (SSE). Background task survives client disconnect.
- `POST /api/protocols/run/with-context` — Same with multipart file upload (RAG context).
- `POST /api/pipelines/run` — Execute multi-step pipeline. `POST /api/pipelines/resume/{run_id}` to resume from checkpoint.
- `GET /api/runs` — List runs. `GET /api/runs/{id}` — Run details + outputs. `DELETE /api/runs/{id}` — Delete.
- `GET /api/reports/{run_id}/pdf` — Download PDF (WeasyPrint). `GET /share/{run_id}` — Public HTML.
- `GET /api/protocols` — Protocol manifest. `GET /api/protocols/{key}/stages` — Stage diagram data.
- `GET /api/agents` — Agent registry (builtin + DB overrides). CRUD for custom agents.
- `GET /api/pipelines` — Pipeline presets + custom. CRUD.
- `GET /api/teams` — Team management. CRUD.

### Frontend Pages
Dashboard, RunHistory, RunDetail, ProtocolLibrary, AgentRegistry, Pipelines, Teams, KnowledgeExplorer, ToolsHub, Settings.

### Database (SQLModel + Postgres)
Models: `Run`, `RunStep` (pipeline checkpoints), `AgentOutput`, `Agent` (custom overrides), `Pipeline`, `PipelineStep`, `Team`, `Integration`. Auto-migration at startup for new columns.

## Diagram Conventions

When creating or editing Mermaid diagrams in `protocol-diagrams/`:
- `([Text]):::agent` — Agent nodes | `[Text]:::stage` — Processing stages | `{Text}:::decision` — Decision gates
- Category colors: Meta `#607D8B` | Baselines `#4A90D9` | Liberating Structures `#9B59B6` | Intelligence `#E74C3C` | Game Theory `#F39C12` | Org Theory `#1ABC9C` | Systems `#2ECC71` | Design `#E91E63`

## Observability

All 53 protocols have built-in observability via two layers:

**Langfuse tracing** (`protocols/langfuse_tracing.py`): Every orchestrator's `run()` method is decorated with `@trace_protocol("p{NN}_name")`, which creates a root span in Langfuse Cloud. LLM calls within a trace are recorded as child spans via `record_generation()`. Requires `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_BASE_URL` in `.env`. Uses `start_observation(as_type="span")` (Langfuse v4+ — `start_span()` was removed). Wrapped in try/except so tracing failures never block protocol execution.

**Postgres persistence** (`protocols/persistence.py`): Every CLI `run.py` calls `persist_run()` after execution, writing the run metadata, result JSON, and Langfuse trace_id to the `runs` table. Agent-level outputs are extracted where the result format supports it. Uses `ce-db` package with async SQLAlchemy + asyncpg. Default connection: `postgresql+asyncpg://ce:ce_local@localhost:5432/ce_platform` (Docker Compose).

**Schema note**: there are **two** run-tracking schemas in this DB — `run` (old SQLModel, powers the UI) and `runs` (Alembic-managed, audit sink). Both are load-bearing. See [`docs/schema.md`](docs/schema.md) for the contract and failure-mode cheat sheet.

**Preflight checks** (`protocols/_preflight.py`): Every CLI invocation prints a banner and validates Langfuse, `ce_db`, Postgres reachability, and Alembic head. In dev these are warnings; pass `--strict` or set `ENV=production` / `CE_PREFLIGHT_STRICT=1` to abort on any FAIL. Escape hatch: `CE_SKIP_PREFLIGHT=1`.

**Infrastructure**: `docker-compose.yml` runs Postgres. Langfuse uses Langfuse Cloud (`us.cloud.langfuse.com`) — self-hosted config is commented out in docker-compose.yml.

```bash
# Check runs in Postgres
docker exec ce-agents-postgres-1 psql -U ce -d ce_platform \
  -c "SELECT protocol_key, status, langfuse_trace_id, started_at FROM runs ORDER BY created_at;"
```

## Important Context

- The adaptive router uses **Cynefin framework** as meta-logic (Clear/Complicated/Complex/Chaotic → different protocol families)
- Protocols are **agent-agnostic orchestration patterns** — not tied to C-Suite or any specific agent collection
- "C-Suite" agents (CEO, CFO, CTO, CMO, COO, CPO, CRO) are defined in `CE - Agent Builder/` — prompts, tools, and memory. Orchestration imports them via `ServerAgent`.
- **ServerAgent replaced SdkAgent** (2026-03-31): `SdkAgent` spawned Claude Code subprocesses which fail as root in Docker. `ServerAgent` uses direct Anthropic API calls. The old `AgentBridge` wrapper is gone from orchestration.
- **Tool execution**: `api/tool_executor.py` dispatches tool calls to handlers in `CE - Agent Builder/src/csuite/tools/registry.py`. All 26 tools (SEC EDGAR, GitHub, Census, BLS, Brave, Notion, Pinecone, pricing, image gen, web search, etc.) work via this path.
