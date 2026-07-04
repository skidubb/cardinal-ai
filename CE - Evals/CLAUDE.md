# CLAUDE.md — CE - Evals

LLM-as-judge evaluation framework. **Library-only** — no CLI; import and use programmatically.

## Layout

```
src/ce_evals/core/
├── judge.py           # Judge orchestration
├── judge_backends.py  # Claude, GPT-4, Gemini judge backends
├── rubric.py          # Shared scoring rubric
├── runner.py          # Eval runner
├── models.py          # Pydantic models
└── cost.py            # Cost tracking (pricing from ce-shared)
```

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -e .
pytest tests/ -m "not integration"    # CI default; integration tests hit real APIs
```

## Conventions

Same as the monorepo root [CLAUDE.md](../CLAUDE.md): Python 3.11+, async, Ruff (E,F,I,N,W,UP; line 100), Pydantic v2, `@pytest.mark.integration` for real API calls.

**Critical**: eval scores produced against `research`-mode agents are invalid — agents must run in `production` mode (see root CLAUDE.md, Agent Mode).

`assessments/` and `rubrics/` hold human-authored assessment documents, not code.
