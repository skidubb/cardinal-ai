# CLAUDE.md — ce-db

Shared Postgres layer: async SQLAlchemy + asyncpg + Alembic migrations. Schema for runs, traces, and costs, consumed by `CE - Multi-Agent Orchestration` (and optionally CE - Evals) via `ce-db @ file:../ce-db` in requirements.

## Layout

```
src/ce_db/
├── engine.py     # Async engine factory
├── session.py    # Session management
└── models/       # SQLAlchemy models (runs, traces, costs, insights)
alembic/          # Migrations — always add schema changes as a new revision
```

## Rules

- Never edit an applied migration; create a new Alembic revision (`alembic revision --autogenerate`).
- Runs carry a `tenant_id` scoping column — every new run-adjacent table must too (multi-tenant partitioning).
- There are **two** run-tracking schemas in the production DB: `run` (old SQLModel, powers the UI) and `runs` (Alembic-managed audit sink). Both are load-bearing — see `CE - Multi-Agent Orchestration/docs/schema.md` before touching either.
- Local Postgres + migrations: `bash scripts/dev-bootstrap.sh` from the repo root.

Conventions per root [CLAUDE.md](../CLAUDE.md).
