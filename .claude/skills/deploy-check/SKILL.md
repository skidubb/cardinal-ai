---
name: deploy-check
description: Pre-deploy checklist for the Railway backend and Vercel portal. Use before pushing to the production branch, deploying, or when asked "is this safe to ship".
---

# Deploy Check

Production topology: Railway runs the FastAPI engine (multi-stage Dockerfile, healthcheck `/api/health`) from the branch configured in Railway; Vercel runs `cardinal-portal` (auto-deploy on push). Confirm the CURRENT production branch in Railway settings before assuming — the repo docs record it, but Railway is the source of truth.

## Backend (Railway) checklist

1. `ruff check protocols/ api/ --ignore E402` and `pytest tests/ -m "not integration"` green in `CE - Multi-Agent Orchestration`.
2. UI builds: `cd ui && npx vite build`.
3. New DB schema? Must be an Alembic revision in `ce-db/alembic/` — never a hand-edited table. Remember the two load-bearing run schemas (`run` + `runs`) — see `docs/schema.md`.
4. `/api/health` returns `"status": "ok"` locally, including `"agent_builder": "ok"` — a `degraded` value means ServerAgent will run tool-less; do not ship it.
5. Single Uvicorn worker only — SSE queues are in-process; multi-worker silently drops events.
6. New env vars registered in `ce-shared` `KEY_REGISTRY` AND set in Railway before the deploy.
7. `python scripts/check-doc-drift.py --fs-only` clean from repo root.

## Portal (Vercel) checklist

1. `npx tsc --noEmit` clean in `cardinal-portal/`.
2. Clerk keys/env present in Vercel project settings (never committed).
3. Confirm the exact Vercel project name before deploying — never deploy to a guessed target.

## After deploy

- Watch the Railway deploy logs for `DEGRADED:` lines (Agent Builder import failures).
- Hit `/api/health` on the deployed URL and verify `agent_builder: ok`.
