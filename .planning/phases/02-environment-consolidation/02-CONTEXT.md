# Phase 2: Environment Consolidation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Consolidate all API keys into a single root `.env`, make all projects load from it deterministically, and eliminate per-project `.env` files. Includes Docker credential consolidation and a diagnostic tool for env health.

</domain>

<decisions>
## Implementation Decisions

### Env Loading Strategy
- ce-shared provides `find_and_load_dotenv()` utility that walks up from CWD to find root `.env`
- Loads into `os.environ` so pydantic-settings `env_file` and raw `os.environ.get()` both work without changes
- Shell-exported vars take precedence over `.env` file values (standard dotenv behavior — don't override)
- Delete all 3 per-project `.env` files (Agent Builder, Orchestration, Evals)
- Single `.env.example` at repo root with all keys documented
- Each project calls `find_and_load_dotenv()` at startup instead of local dotenv loading

### Validation Strictness
- Tiered validation: missing required keys cause immediate startup failure, missing optional keys log a warning
- ce-shared defines a centralized `KEY_REGISTRY` mapping key names to metadata (required_by, description, category)
- Projects import their required key set from the registry
- Rich error messages on missing required keys: key name + purpose + how to fix (e.g., "Add it to .env at repo root or export in shell")
- Validation runs automatically when `find_and_load_dotenv()` is called — one call does load + validate

### Docker Credentials
- docker-compose.yml uses `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}`, `${POSTGRES_DB}` variable interpolation from root `.env`
- Metabase service also reads from root `.env` vars: `MB_DB_PASS=${POSTGRES_PASSWORD}`, `MB_DB_USER=${POSTGRES_USER}`
- ce-db loads root `.env` via ce-shared's loader — no hardcoded DATABASE_URL fallback
- Individual Postgres vars in root `.env` (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB, POSTGRES_PORT)
- ce-db constructs DATABASE_URL from individual vars in code — docker-compose and Python use the same source vars

### env_check Diagnostic
- `python -m ce_shared.env_check` reports present/missing status with redacted values (no connectivity tests)
- Output grouped by project (Agent Builder keys, Orchestration keys, etc.)
- Rich tables with color-coded status (green=set, red=missing) — ce-shared adds Rich as dependency
- Reports which `.env` file was loaded (full path) at top of output
- Warns if stale per-project `.env` files are found ("Stale .env found in CE - Agent Builder/ — should be deleted")

### Claude's Discretion
- Internal structure of the env module within ce-shared (single file vs subpackage)
- Exact KEY_REGISTRY data structure and how projects declare their required keys
- How `find_and_load_dotenv()` traverses directories (pathlib parents vs os.walk)
- Whether env_check supports any CLI flags (--verbose, --project, etc.)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ce-shared/` package: Already exists from Phase 1 with hatchling build. New env module adds alongside pricing module.
- `CE - Agent Builder/src/csuite/config.py`: Uses `pydantic-settings` with `SettingsConfigDict(env_file=".env")`. After loading root .env into os.environ, pydantic-settings picks up values automatically — minimal changes needed.
- `CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py`: Has `load_dotenv()` call pattern — replace with ce-shared loader.

### Established Patterns
- `ce-shared` uses `src/ce_shared/` layout with hatchling build and editable install
- Agent Builder already depends on Rich for terminal output
- Both Agent Builder and Orchestration already have ce-shared as editable dependency (from Phase 1)
- Pydantic-settings `extra="ignore"` means unknown env vars are silently skipped — good for shared .env

### Integration Points
- Agent Builder: Replace `env_file=".env"` in Settings with call to ce-shared loader before Settings init
- Orchestration: Replace 4+ scattered `load_dotenv()` calls with single ce-shared loader call in module init
- ce-db: Replace `os.environ.get("DATABASE_URL", hardcoded_default)` with ce-shared loader + URL construction
- docker-compose.yml: Replace hardcoded values with `${VAR}` interpolation
- ce-shared pyproject.toml: Add `python-dotenv` and `rich` as dependencies

</code_context>

<specifics>
## Specific Ideas

- The loader should be the "one function to call" — callers shouldn't need to know about path traversal, validation, or override semantics
- env_check should feel like a health dashboard for the monorepo — "are all my keys in order?"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-environment-consolidation*
*Context gathered: 2026-03-09*
