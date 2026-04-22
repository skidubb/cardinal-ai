# Schema — `run` vs `runs` (it's not a bug)

Two Postgres table families coexist in the `ce_platform` database. They serve different purposes and are both load-bearing. This document exists because the naming confuses every new contributor (and caused an afternoon of debugging on 2026-04-22).

## TL;DR

| Tables | Schema owner | Writers | Readers | Purpose |
|---|---|---|---|---|
| `run`, `agentoutput`, `runstep`, `pipeline`, `pipelinestep`, `team`, `integration` | Hand-coded SQLModel in `api/database.py` | `api/runner.py`, `api/routers/*.py` | `api/routers/runs.py`, portal UI via `/api/runs` | **Application state.** Powers the web UI's run history, run detail pages, pipeline execution tracking. |
| `runs`, `agent_outputs`, `agents`, `protocol_insights`, `run_learnings`, `eval_*` | Alembic-managed in `ce-db` package | `protocols/persistence.py:persist_run()` (called by every CLI and the API post-run hook) | None yet | **Audit/telemetry sink.** Durable record of every protocol run for cost analytics, Langfuse cross-reference, cross-project evals. Written from both CLI and API; no consumer in the codebase today. |

Rule of thumb:
- If you want to **show** a run to a user (API, UI), use `run`.
- If you want to **record** a run for durable audit/eval, use `persist_run()` → `runs`.

## Why two?

These tables are the artifact of a migration that started but did not finish. `ce-db` was introduced to standardize persistence across the monorepo (Agent Builder, Evals, Orchestration) via Alembic-managed migrations. The API server's existing `run` schema was never migrated — the UI contracts (`/api/runs`, `/api/runs/{id}`, run delete) depend on it directly.

Unifying them is a **2–4 week project**: rewrite API reads against `runs`, rewrite UI API client to the new shape (different field names, different cascades), dual-write for one release, then drop the old tables. It is not a resilience concern; it is a product-level cleanup. Until someone schedules it, both tables stay.

## The contract

Both write paths MUST succeed. Silent failure of either is an **incident**, not an acceptable degradation.

1. **`Run()` SQLModel writes** (old) — if these fail, the UI shows wrong data and run detail pages break. API startup fails fast on DB unreachable; runtime failures bubble to 5xx.
2. **`persist_run()` writes** (new) — historically wrapped in broad `try/except` that silently no-op'd. As of the 2026-04-22 resilience pass, preflight checks (see `protocols/_preflight.py`) detect the common silent failures (missing `ce_db` install, schema drift, DB unreachable) at CLI startup. Use `--strict` to abort rather than degrade.

Do not add new `try/except: pass` around either write path without explicit approval.

## Alembic head

Current head revision: **`004_add_tenant_slug_to_runs`**. When a new migration lands, update `_HEAD_REVISION_EXPECTED` in `protocols/_preflight.py`. The preflight check compares `alembic_version.version_num` to that constant.

Apply locally: `cd ce-db && alembic upgrade head`. Apply on Railway: already automatic via the deploy step.

## Failure-mode cheat sheet

| Symptom | Likely cause | Fix |
|---|---|---|
| `relation "runs" does not exist` when `persist_run()` runs | Alembic migrations never applied to the target DB | `cd ce-db && alembic upgrade head` |
| `ce-db is not importable; run persisted only in local runtime surfaces` | `ce_db` not installed editable in the venv | `pip install -e ../ce-db ../ce-shared` (both — ce-db's install can stomp the editable ce-shared) |
| UI run list is empty but CLI runs completed | CLI writes to `runs`; UI reads `run`. Correct behavior. | Nothing — they're disjoint. |
| Preflight says `[ok] Postgres` but `[FAIL] Alembic` | `DATABASE_URL` points at a Postgres that exists but hasn't been migrated (e.g., a container with the old `run` schema only) | Either migrate that DB, or point `DATABASE_URL` at a DB that has been migrated. |
| Preflight says `[FAIL] Langfuse: key is set but client never initialized` | `.env` loaded after `protocols.langfuse_tracing` was imported. The decorator silently degrades to a passthrough. | Add `find_and_load_dotenv()` at the top of the module doing the import, BEFORE any `from protocols.langfuse_tracing import ...`. See `protocols/p53_contract_net/orchestrator.py:16-19` for the canonical pattern. |

## See also

- `protocols/_preflight.py` — the checks enforcing this contract
- `protocols/persistence.py` — the `persist_run()` entry point
- `ce-db/src/ce_db/models/runs.py` — the new schema definition
- `CE - Multi-Agent Orchestration/api/database.py` — the old schema definition
