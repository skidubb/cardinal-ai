# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Monorepo for Cardinal Element's agentic AI work. Consolidates three previously separate repos (`ce-c-suite`, `coordination-lab`, `CE-Evals`) plus automation workflows. Owner: Scott Ewalt / Cardinal Element — an AI-native growth architecture consultancy.

## Projects

| Directory | What it is | Setup |
|-----------|-----------|-------|
| `CE - Agent Builder/` | C-Suite CLI app — 7 executive AI agents with synthesis, debate, audit | `pip install -e ".[dev]"` (hatchling) |
| `CE - Multi-Agent Orchesration/` | 48 coordination protocols + 56-agent registry + evaluation harness | `pip install -r requirements.txt` |
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

### CE - Multi-Agent Orchesration
```bash
cd "CE - Multi-Agent Orchesration"
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run any protocol
python -m protocols.p06_triz.run -q "Should we expand?" -a ceo cfo cto
python -m protocols.p04_multi_round_debate.run -q "..." -a ceo cfo cto --rounds 3

# All protocols accept: -q, -a, --thinking-model, --orchestration-model
# Multi-round protocols also accept: --rounds/-r

# Evaluation harness
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
```

## Architecture

### CE - Agent Builder — Two Independent Agent Systems

1. **Claude Code agents** (`~/claude-dotfiles/agents/*.md`) — 7 executives + 30 sub-agents invoked via Task tool. Executives use `model: opus`, sub-agents use `model: sonnet/haiku`.

2. **Python CLI agents** (`src/csuite/`) — Click CLI with dual backend: legacy `BaseAgent` subclasses (direct Anthropic API) or `SdkAgent` (claude-agent-sdk with MCP tools). Controlled by `AGENT_BACKEND` env var. Both expose `async chat(message) -> str`.

These two systems are **not connected** — independent implementations sharing the same role definitions.

Key flows: Orchestrator runs agents in parallel via `asyncio.gather` → synthesis prompt. Debate runs N sequential rounds (agents parallel within each round). Audit is a sequential 7-agent pipeline.

### CE - Multi-Agent Orchesration — Protocol Pattern

Every protocol lives in `protocols/p{NN}_{name}/` with: `orchestrator.py` (async class with `run(question)`), `prompts.py` (string constants), `run.py` (CLI). Agents are simple dicts `{"name": str, "system_prompt": str}` — no classes. Two model tiers: `thinking_model` (Opus) for reasoning, `orchestration_model` (Haiku) for mechanical steps. 48 protocols across 8 categories (see project-level `CLAUDE.md` for taxonomy).

Shared agent registry: `protocols/agents.py` — 56 agents across 14 categories, supports `@category` group syntax.

### CE - Evals

Library-only (no CLI). Core in `src/ce_evals/core/` — `judge.py` + `judge_backends.py` (Claude/GPT-4/Gemini), `rubric.py`, `runner.py`, `cost.py`. Import and use programmatically.

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
- `CE - Multi-Agent Orchesration/CLAUDE.md` — Protocol architecture, taxonomy, diagram conventions
