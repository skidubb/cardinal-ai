# Local Dev Setup

One command brings a fresh machine to a working state:

```bash
bash scripts/dev-bootstrap.sh
```

The script is idempotent — re-running after a partial failure or after a few weeks of drift is safe.

## What it does

1. **Picks a free Postgres host port.** Default is 5432. If held by a non-ce-agents container (e.g. `on3-postgres`, `topicletter-postgres`), probes 5434..5440 and picks the first free one. Writes `DATABASE_URL` to `.env.local` when non-5432.
2. **Starts `ce-agents-postgres`** via `docker compose up -d postgres` when it's the 5432 case. Skips when another container holds the port (the current `docker-compose.yml` hardcodes 5432:5432; non-5432 requires manual Postgres setup).
3. **Hard-checks DB identity** before destructive actions. Refuses to run migrations unless `POSTGRES_DB=ce_platform` and `POSTGRES_USER=ce` on the target container.
4. **Installs `ce-shared`, `ce-db`, `ce-graph` editable** into each project's venv, in dependency order (ce-shared first; otherwise ce-db's install resolves ce-shared from PyPI and stomps the editable copy — we hit this bug on 2026-04-22).
5. **Runs `alembic upgrade head`** against the chosen port.
6. **Sanity round-trip**: runs P53 in research mode (no LLM calls, no cost) and confirms a row appears in the `runs` table.

## Flags

| Flag | Effect |
|---|---|
| `--dry-run` | Print the plan; no destructive actions. |
| `--non-interactive` | Never prompt; fail on decisions. Default in CI/non-TTY. |
| `--skip-sanity-run` | Don't execute the P53 round-trip. |

## Env overrides

| Variable | Effect |
|---|---|
| `CE_BOOTSTRAP_PORT=N` | Force a specific host port. |
| `CE_SKIP_CONTAINER=1` | Don't touch docker; assume Postgres is already up. |

## Common scenarios

### "Everything was fine last week, now nothing works"

Run `bash scripts/dev-bootstrap.sh`. Usually the cause is:
- `ce-db` got uninstalled (something else installed a conflicting dep)
- Another project grabbed port 5432
- Alembic drifted behind (new migration landed on `main`)

The script detects and fixes all three.

### "Port 5432 is held by on3-postgres (or another project)"

Two honest options:

1. **Let them share the port**: stop on3, start ce-agents. `docker stop on3-postgres && bash scripts/dev-bootstrap.sh`. On3 data is preserved in its volume.
2. **Run ce-agents on a different port**: the script picks 5434 automatically and writes `.env.local`. You then need to manually start a ce-agents Postgres on 5434 (the current `docker-compose.yml` doesn't support this) — typically:
   ```bash
   docker run -d --name ce-agents-postgres-5434 \
     -e POSTGRES_DB=ce_platform -e POSTGRES_USER=ce -e POSTGRES_PASSWORD=ce_local \
     -p 5434:5432 -v ce_agents_pgdata:/var/lib/postgresql/data postgres:16
   CE_BOOTSTRAP_PORT=5434 bash scripts/dev-bootstrap.sh
   ```

### "The sanity run failed but everything else is green"

Check `/tmp/dev-bootstrap-sanity.log`. Most common cause: `ANTHROPIC_API_KEY` isn't in `.env` (research mode shouldn't need it, but agent-provider still validates). Either fix `.env` or re-run with `--skip-sanity-run`.

### "Migrations failed with 'relation X does not exist'"

Alembic is trying to run against a DB that has a partial old schema. Either:
- `cd ce-db && alembic downgrade base && alembic upgrade head` (rebuilds cleanly; **deletes all rows in the ce-db tables** — safe for local dev, never do this on Railway)
- Start fresh: `docker compose down -v && bash scripts/dev-bootstrap.sh` (**deletes the whole Postgres volume**)

## Verification after bootstrap

```bash
cd "CE - Multi-Agent Orchestration" && source venv/bin/activate
python -m protocols.p53_contract_net.run -q "hello" -a ceo --strict
# Expect: banner shows [ok] on all four preflight checks, protocol runs, persist_run succeeds.

# Confirm the row landed in Postgres:
docker exec ce-agents-postgres-1 psql -U ce -d ce_platform \
  -c "SELECT protocol_key, status, started_at FROM runs ORDER BY started_at DESC LIMIT 3;"
```

## Wiring CLI runs into the cardinal-portal UI

Bootstrap gives you a working CLI + Postgres. To see those runs in the portal UI at `http://localhost:3001/runs`, you need three more pieces:

### 1. CLI tenant matches your portal Clerk org

The portal filters runs by the signed-in org's slug. CLI runs are tagged via `CE_DEV_TENANT`. Align them:

```bash
# in repo root .env
CE_DEV_TENANT=cardinal-element   # or whatever your Clerk org slug is
```

If unset, CLI writes land under `local-dev` and won't be visible to a `cardinal-element` portal session.

### 2. Portal points at local FastAPI

In `cardinal-portal/.env.local`:

```
NEXT_PUBLIC_RAILWAY_API_URL=http://localhost:8000
```

Restart the Next.js dev server after changing this (NEXT_PUBLIC_* vars are read at startup).

### 3. FastAPI is running on 8000

```bash
cd "CE - Multi-Agent Orchestration" && source venv/bin/activate
uvicorn api.server:app --port 8000 --host 127.0.0.1
```

Keep this running in its own terminal (or use `nohup ... > /tmp/uvicorn.log 2>&1 &` for a detached session).

### Verifying the chain works

```bash
# 1. API is reachable
curl -s http://localhost:8000/api/health  # expect {"status":"ok","db":"postgres"}

# 2. Detail endpoint returns a row with tenant filter
curl -s http://localhost:8000/api/runs/<id> | python -m json.tool | head -10

# 3. Run a protocol and refresh http://localhost:3001/runs — the new row should be at the top.
python -m protocols.p57_liquid_democracy.run -q "portal visibility test" -a ceo --strict
```

### Retagging historical rows to the portal tenant

Any CLI runs written before step 1 was in place will still have `tenant_slug='local-dev'` and be invisible to a `cardinal-element` portal session. Retag safely:

```sql
-- Scoped to CLI-origin rows only; will NOT touch API-originated data.
UPDATE run  SET tenant_slug='cardinal-element' WHERE tenant_slug='local-dev' AND type IN ('backfill','single');
UPDATE runs SET tenant_slug='cardinal-element' WHERE tenant_slug='local-dev' AND source IN ('backfill','cli');
```

Run via `docker exec on3-postgres psql -U ce -d ce_platform -c "<sql>"` or your local equivalent.

## Related docs

- Preflight contract: `CE - Multi-Agent Orchestration/protocols/_preflight.py` (check implementation)
- Schema dual-track: `CE - Multi-Agent Orchestration/docs/schema.md` (why `run` and `runs` both exist)
- Repo overview: `CLAUDE.md` (at the repo root)
