# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Monorepo for Cardinal Element's agentic AI work. Consolidates three previously separate repos (`ce-c-suite`, `coordination-lab`, `CE-Evals`) plus automation workflows. Owner: Scott Ewalt / Cardinal Element — an AI-native growth architecture consultancy.

## Projects

| Directory | What it is | Setup |
|-----------|-----------|-------|
| `CE - Agent Builder/` | C-Suite CLI app — 7 executive AI agents with synthesis, debate, audit | `pip install -e ".[dev]"` (hatchling) |
| `CE - Multi-Agent Orchestration/` | 53 coordination protocols + 56-agent registry + FastAPI web UI | `pip install -r requirements.txt` |
| `CE - Evals/` | LLM-as-judge evaluation framework (Claude, GPT-4, Gemini backends) | `pip install -e .` (setuptools) |
| `n8n Workflows/` | n8n automation workflow JSON exports | N/A (imported into n8n) |

Each project has its own venv. Always activate the project-specific venv before running commands.

## Quick Reference Commands

### CE - Agent Builder
```bash
cd "CE - Agent Builder"
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# CLI
csuite ceo "question"                           # Single agent query
csuite synthesize "question" -a cfo cto         # Multi-agent synthesis
csuite debate "question" -a cfo cto cmo -r 3    # Multi-round debate
csuite interactive                              # Interactive mode (@ceo, @all, @debate)
csuite audit "description" --revenue "$12M" --employees 45

# Dev
pytest tests/ -m "not integration"              # Unit tests (CI default)
pytest tests/test_foo.py -k "test_name"         # Single test
ruff check src/ mcp_servers/                    # Lint
mypy src/csuite --ignore-missing-imports        # Type check
streamlit run demo/app.py                       # Demo UI
```

### CE - Multi-Agent Orchestration
```bash
cd "CE - Multi-Agent Orchestration"
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run any protocol
python -m protocols.p06_triz.run -q "Should we expand?" -a ceo cfo cto
python -m protocols.p04_multi_round_debate.run -q "..." -a ceo cfo cto --rounds 3

# All protocols accept: -q, -a, --thinking-model, --orchestration-model, --mode
# Multi-round protocols also accept: --rounds/-r
# Default mode is "production" (real SDK agents). Use --mode research for lightweight dicts.
# Or set AGENT_MODE=research env var to override globally.

# Evaluation harness
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
```

## Architecture

### CE - Agent Builder — The Agent Factory

**Agent definitions** (`src/csuite/`) — 70+ role-specific system prompts (`agents/sdk_agent.py:_ROLE_PROMPTS`), 26 tool schemas (`tools/schemas.py:ALL_TOOL_SCHEMAS`), per-role tool mappings for 40+ roles (`tools/registry.py:ROLE_TOOL_MAP`), and tool handlers dispatched via `tools/registry.py:execute_tool()`. Also includes Pinecone memory, DuckDB learning, and session persistence for CLI use.

**Two agent backends for CLI**: `BaseAgent` (direct Anthropic API with tool loop) and `SdkAgent` (Claude Agent SDK subprocess). For **server/Docker deployment**, neither is used — see ServerAgent below.

**Scott's personal agents** (`~/claude-dotfiles/agents/*.md`) — 7 executives + 30 sub-agents invoked via Claude Code Task tool. These are NOT the product — they're Scott's personal Claude Code agent teams.

### CE - Multi-Agent Orchestration — Protocol Engine + Web UI

Every protocol lives in `protocols/p{NN}_{name}/` with: `orchestrator.py` (async class with `run(question)`), `prompts.py` (string constants), `run.py` (CLI). Two model tiers: `thinking_model` (Opus) for reasoning, `orchestration_model` (Haiku) for mechanical steps. 53 protocols across 8+ categories (see project-level `CLAUDE.md` for taxonomy).

**ServerAgent** (`protocols/server_agent.py`): The production agent class for server deployment. Uses direct `anthropic.AsyncAnthropic().messages.create()` with native tool-use loop (max 15 iterations). Imports role prompts and tool schemas from Agent Builder. No subprocess spawning — works in Docker/Railway. `build_production_agents()` in `protocols/agent_provider.py` creates these.

**Research mode**: `--mode research` or `AGENT_MODE=research` uses lightweight dicts without tools/memory. Production is default.

**Web UI**: FastAPI backend (`api/`) + React frontend (`ui/`). SSE streaming for live run progress. PDF reports via WeasyPrint. Deployed on Railway.

**Agent registry**: `protocols/agents.py` — 56 agents across 14 categories, supports `@category` group syntax.

**Observability**: All protocols have Langfuse tracing (`@trace_protocol` decorator) and Postgres persistence. Both degrade gracefully if unavailable.

### CE - Evals

Library-only (no CLI). Core in `src/ce_evals/core/` — `judge.py` + `judge_backends.py` (Claude/GPT-4/Gemini), `rubric.py`, `runner.py`, `cost.py`. Import and use programmatically.

### Shared Packages

- **`ce-shared/`**: Pricing (`MODEL_PRICING`, `cost_for_model()`), env registry (`KEY_REGISTRY`, `find_and_load_dotenv()`). Used by all projects. Single source of truth for model pricing and env var names.
- **`ce-db/`**: Async SQLAlchemy + asyncpg + Alembic migrations. Postgres schema for runs, traces, costs. Used by Orchestration and optionally Evals.

### Deployment

Production runs on **Railway.app** from branch `claude/add-rc-config-support-W9iw7`. Multi-stage Dockerfile: Node build (React UI) → Python runtime with system deps (cairo, pango for WeasyPrint). Railway Postgres addon for DB. `railway.toml` configures healthcheck at `/api/health`.

## Conventions

- **Python 3.11+** across all projects
- **Async everywhere** — `AsyncAnthropic`, `asyncio.gather`, `async def`
- **Ruff** for linting (rules: E, F, I, N, W, UP; line length 100)
- **mypy** with `check_untyped_defs` (not strict)
- **Pydantic v2** for models and settings
- **Tests**: `@pytest.mark.integration` for real API calls; CI runs `-m "not integration"`
- **Model policy**: `claude-opus-4-6` for executives, `claude-haiku-4-5-20251001` for orchestration/mechanical steps
- **Protocol naming**: `p{NN}_{descriptor}` (e.g., `p06_triz`, `p16_ach`)
- **Agent keys**: kebab-case (e.g., `ceo-board-prep`, `gtm-vp-sales`)

## Environment

Each project requires `.env` with at minimum `ANTHROPIC_API_KEY`. Copy from `.env.example` in each project. Pinecone, Notion, and other integrations are optional and degrade gracefully.

## Project-Level Documentation

Each project has its own detailed CLAUDE.md with full architecture docs:
- `CE - Agent Builder/.claude/CLAUDE.md` — CLI commands, agent system architecture, all patterns
- `CE - Multi-Agent Orchestration/CLAUDE.md` — Protocol architecture, taxonomy, diagram conventions
