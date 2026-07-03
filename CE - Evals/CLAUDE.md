# CE - Evals — CLAUDE.md

Project-level guidance for Claude Code sessions working on the `ce-evals` evaluation toolkit.

## What this project is

**Library-only** LLM-as-a-judge framework for scoring multi-agent protocol outputs. No CLI. Import and use programmatically. Backends: Claude, GPT-4, Gemini.

## Setup

```bash
cd "CE - Evals"
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"                # unit tests
pip install -e ".[db,dev]"             # add ce-db for persistence
```

Requires `ANTHROPIC_API_KEY` (and optionally `OPENAI_API_KEY`, `GEMINI_API_KEY` for cross-model judging) in `.env`.

## Programmatic use

```python
from ce_evals import Judge, Rubric, Runner

rubric = Rubric.from_yaml("rubrics/strategic_recommendation.yaml")
judge = Judge(backend="claude", rubric=rubric)
result = await judge.score(protocol_output)
```

Or via the runner for batches:

```python
from ce_evals.core.runner import EvalRunner

runner = EvalRunner(rubric=rubric, backend="claude")
scores = await runner.run(protocol_run_ids=[...])
```

## Dev

```bash
pytest tests/ -m "not integration"     # unit tests
pytest tests/                          # includes real-API integration
```

## Architecture

Everything is in `src/ce_evals/`:

| Module | Purpose |
|---|---|
| `core/judge.py` | The judge orchestrator — takes rubric + output → scored result |
| `core/judge_backends.py` | Claude / GPT-4 / Gemini backend adapters |
| `core/rubric.py` | Rubric loading and validation (Pydantic models) |
| `core/runner.py` | Batch runner over multiple protocol outputs |
| `core/cost.py` | Judge-cost tracking |
| `core/models.py` | Shared Pydantic types |
| `protocols/` | Protocol-specific eval helpers |
| `report/` | Report rendering from scored batches |
| `rubrics/` | YAML rubric definitions (top-level in project) |
| `assessments/` | Saved assessment runs |
| `snapshots/` | Reference outputs for regression |

## Conventions

- **Python 3.11+**, async everywhere.
- **Pydantic v2** for rubrics and results.
- Rubrics are declarative YAML; the runtime never edits them.
- **Judge cost tracking is mandatory** — every scored batch must record cost via `cost.py`.
- Backends are pluggable via `judge_backends.py`; add new ones there, not by editing `judge.py`.
- **Tests**: `@pytest.mark.integration` on real-API tests; CI runs `-m "not integration"`.

## Where this fits in the monorepo

- **Orchestration** (`CE - Multi-Agent Orchestration`) produces protocol run outputs (persisted to Postgres `runs` table).
- **Evals** scores those outputs against rubrics.
- **Roadmap**: scores auto-flow into `router_weights` (Postgres) to close the P45 → P0a adaptive-router loop. Today the scores land in `assessments/` and Langfuse dataset scores; nothing reads them back yet.

## Files worth knowing

- `src/ce_evals/core/judge.py` — the main entry point
- `src/ce_evals/core/rubric.py` — rubric schema
- `rubrics/*.yaml` — production rubrics
- `examples/run_protocol_eval.py` — how to score a protocol run end-to-end
- `CE-AGENTS Unified Assessment Rubric.xlsx` — reference rubric spec (source of truth for scoring dimensions)
