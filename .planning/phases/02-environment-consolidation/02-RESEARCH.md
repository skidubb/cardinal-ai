# Phase 2: Environment Consolidation — Research

**Researched:** 2026-03-09
**Researcher:** Claude Opus 4.6
**Phase requirements:** ENVR-01 through ENVR-09

---

## 1. Current State Analysis

### 1.1 Existing .env Files

There are **3 live .env files** and **4 .env.example templates**:

| File | Keys | Notes |
|------|------|-------|
| `CE - Agent Builder/.env` | 12 keys | ANTHROPIC, OPENAI, GOOGLE, XAI, PINECONE, DATA_GOV, SEC_EDGAR, CENSUS, BLS, BRAVE, NOTION, DUCKDB_PATH |
| `CE - Multi-Agent Orchestration/.env` | 8 keys | ANTHROPIC, OPENAI, GOOGLE, XAI, PINECONE, LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL |
| `CE - Evals/.env` | 5 keys | ANTHROPIC, OPENAI, GOOGLE, XAI, PINECONE |
| `.env.example` (root) | 7 keys | Incomplete — missing many keys from sub-projects |
| `CE - Agent Builder/.env.example` | 15 keys | Most comprehensive template |
| `CE - Multi-Agent Orchestration/.env.example` | 2 keys | Minimal |
| `CE - Agent Builder/demo/.env.example` | 1 key | ANTHROPIC only |

**Key observations:**
- **No root `.env` file exists** — only `.env.example` at root
- Agent Builder and Orchestration have **different ANTHROPIC_API_KEY values** (different API keys)
- Evals shares the same ANTHROPIC_API_KEY as Agent Builder
- Agent Builder has unique keys not in other projects: DATA_GOV, SEC_EDGAR, CENSUS, BLS, BRAVE, NOTION, DUCKDB_PATH
- Orchestration has unique keys: LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL
- Root `.env.example` uses `NOTION_TOKEN` but Agent Builder uses `NOTION_API_KEY` — naming inconsistency
- Root `.env.example` uses `LANGFUSE_HOST` but Orchestration `.env` uses `LANGFUSE_BASE_URL` — naming inconsistency (langfuse_tracing.py checks both)

### 1.2 Env Loading Patterns

Four distinct patterns are in use:

**Pattern A: `load_dotenv()` at module level (no path argument)**
- `CE - Agent Builder/src/csuite/main.py:25` — `load_dotenv()`
- `CE - Multi-Agent Orchestration/api/server.py:17` — `load_dotenv()`
- `CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/orchestrator.py:19` — `load_dotenv()`
- `CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/team_assignment.py:10` — `load_dotenv()`
- `CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py:40` — `load_dotenv()` (inside try/except ImportError)
- `CE - Agent Builder/scripts/notion_databases.py:31` — `load_dotenv()`
- `CE - Agent Builder/scripts/upsert_dfw_knowledge.py:22` — `load_dotenv()`
- `CE - Agent Builder/scripts/import_to_notion.py:19` — `load_dotenv()`
- `CE - Agent Builder/demo/app.py:56` — `load_dotenv()`

All of these resolve `.env` relative to CWD — fragile if run from a different directory.

**Pattern B: Pydantic-settings with `env_file=".env"` (relative path)**
- `CE - Agent Builder/src/csuite/config.py:21` — `SettingsConfigDict(env_file=".env")`
- `CE - Evals/src/ce_evals/config.py:23` — `model_config = {"env_file": ".env"}`

Both resolve `.env` relative to CWD, same fragility as Pattern A.

**Pattern C: Raw `os.environ.get()` / `os.getenv()` with no dotenv load**
- `ce-db/src/ce_db/engine.py:10` — `DATABASE_URL` with hardcoded fallback
- `CE - Multi-Agent Orchestration/protocols/config.py:14-16` — THINKING_MODEL, ORCHESTRATION_MODEL, BALANCED_MODEL
- `CE - Multi-Agent Orchestration/api/tool_executor.py:37-45` — 8 keys read raw
- `CE - Multi-Agent Orchestration/api/routers/knowledge.py` — PINECONE_API_KEY, PINECONE_INDEX
- Multiple other files across both projects

These depend on env vars being loaded by something else (an earlier `load_dotenv()` or shell export).

**Pattern D: Hardcoded in docker-compose.yml**
- `docker-compose.yml:5-7` — `POSTGRES_DB: ce_platform`, `POSTGRES_USER: ce`, `POSTGRES_PASSWORD: ce_local`
- `docker-compose.yml:28-30` — `MB_DB_USER: ce`, `MB_DB_PASS: ce_local`
- Commented-out langfuse section also has hardcoded `DATABASE_URL`

### 1.3 Docker Compose State

File: `/Users/scottewalt/Documents/CE - AGENTS/docker-compose.yml`

Services:
- **postgres**: Hardcoded `POSTGRES_DB=ce_platform`, `POSTGRES_USER=ce`, `POSTGRES_PASSWORD=ce_local`
- **metabase**: Hardcoded `MB_DB_USER=ce`, `MB_DB_PASS=ce_local`, `MB_DB_HOST=postgres`
- **langfuse**: Commented out (using Langfuse Cloud instead)

The hardcoded `ce_local` password appears in:
1. `docker-compose.yml` (2 places: postgres + metabase)
2. `ce-db/src/ce_db/engine.py` (hardcoded fallback URL)
3. Root `.env.example` DATABASE_URL value

### 1.4 ce-shared Package (from Phase 1)

**Location:** `/Users/scottewalt/Documents/CE - AGENTS/ce-shared/`

**Current structure:**
```
ce-shared/
├── pyproject.toml          # hatchling, name="ce-shared", v0.1.0
└── src/ce_shared/
    ├── __init__.py          # Re-exports pricing module
    └── pricing.py           # MODEL_PRICING, get_pricing(), cost_for_model()
```

**Current dependencies:** None (zero external deps)

**Consumers already depending on ce-shared:**
- `CE - Agent Builder/pyproject.toml` — `"ce-shared @ file:../ce-shared"`
- `CE - Multi-Agent Orchestration/requirements.txt` — `ce-shared @ file:../ce-shared`
- CE-Evals does NOT yet depend on ce-shared

**New dependencies needed for Phase 2:**
- `python-dotenv>=1.0.0` — for `find_and_load_dotenv()`
- `rich>=13.0` — for `env_check` diagnostic (color tables)

### 1.5 Existing Validation

There is **no existing env validation** beyond:
- Pydantic-settings `anthropic_api_key: str = Field(...)` in Agent Builder (required field, fails on empty)
- CE-Evals `anthropic_api_key: str = ""` — empty default, no validation
- Langfuse init checks `os.environ.get("LANGFUSE_SECRET_KEY")` before connecting
- ce-db engine returns `None` if DATABASE_URL empty
- No project has startup validation or early-fail behavior

---

## 2. Complete Key Inventory

### 2.1 API Keys (Secrets)

| Key | Agent Builder | Orchestration | Evals | ce-db | Required By |
|-----|:---:|:---:|:---:|:---:|-------------|
| `ANTHROPIC_API_KEY` | Y | Y | Y | - | All three projects — core dependency |
| `OPENAI_API_KEY` | Y | Y | Y | - | Image gen (AB), evals (Evals), tool executor (Orch) |
| `GOOGLE_API_KEY` | Y | Y | Y | - | Image gen (AB), evals (Evals), tool executor (Orch) |
| `XAI_API_KEY` | Y | Y | Y | - | Grok models via LiteLLM |
| `PINECONE_API_KEY` | Y | Y | - | - | Knowledge base, memory, paper ingestion |
| `LANGFUSE_SECRET_KEY` | - | Y | - | - | Langfuse tracing |
| `LANGFUSE_PUBLIC_KEY` | - | Y | - | - | Langfuse tracing |
| `BRAVE_API_KEY` | Y | (tool_exec) | - | - | Web search tool |
| `NOTION_API_KEY` | Y | (tool_exec) | - | - | Notion integration |
| `GITHUB_TOKEN` | Y | (tool_exec) | - | - | GitHub API, MCP server |
| `DATA_GOV_API_KEY` | Y | - | - | - | Data.gov API |
| `SEC_EDGAR_API_KEY` | Y | - | - | - | SEC EDGAR filings |
| `US_CENSUS_API_KEY` | Y | - | - | - | Census Bureau API |
| `US_BLS_API_KEY` | Y | - | - | - | Bureau of Labor Statistics |

### 2.2 Service URLs & Configuration

| Key | Used In | Default | Notes |
|-----|---------|---------|-------|
| `LANGFUSE_BASE_URL` | Orchestration | (none) | Also checked as `LANGFUSE_HOST` |
| `LANGFUSE_HOST` | Root .env.example | (none) | Alias for LANGFUSE_BASE_URL |
| `DATABASE_URL` | ce-db | `postgresql+asyncpg://ce:ce_local@localhost:5432/ce_platform` | Hardcoded fallback |
| `PINECONE_INDEX_HOST` | Agent Builder, Orch | (none) | GTM knowledge index |
| `PINECONE_LEARNING_INDEX_HOST` | Agent Builder | (none) | Agent memory index |
| `PINECONE_INDEX` | Orchestration API | `ce-gtm-knowledge` | Index name (not host) |

### 2.3 Application Configuration

| Key | Used In | Default | Notes |
|-----|---------|---------|-------|
| `DUCKDB_PATH` | Agent Builder | `./data/agent_memory.duckdb` | Relative path |
| `MEMORY_ENABLED` | Agent Builder | `true` | Toggle memory system |
| `AGENT_BACKEND` | Agent Builder | `legacy` | `legacy` or `sdk` |
| `AGENT_MODE` | Orchestration | `production` | `production` or `research` |
| `DEFAULT_MODEL` | Agent Builder | `claude-opus-4-6` | |
| `HAIKU_MODEL` | Agent Builder config.py | `claude-haiku-4-5-20251001` | |
| `THINKING_MODEL` | Orchestration config.py | `claude-opus-4-6` | |
| `ORCHESTRATION_MODEL` | Orchestration config.py | `claude-haiku-4-5-20251001` | |
| `BALANCED_MODEL` | Orchestration config.py | `claude-sonnet-4-6` | |
| `SESSION_DIR` | Agent Builder | `./sessions` | |
| `REPORTS_DIR` | Agent Builder, Orch | `./reports` | |
| `PROJECT_ROOT` | Agent Builder | `.` | |
| `EVAL_MODEL` | Orchestration multiagent_evals | `claude-haiku-4-5-20251001` | |
| `GOOGLE_CREDENTIALS_PATH` | Agent Builder | (none) | |
| `QUICKBOOKS_CLIENT_ID` | Agent Builder | (none) | Dead stub |
| `QUICKBOOKS_CLIENT_SECRET` | Agent Builder | (none) | Dead stub |
| `QUICKBOOKS_REFRESH_TOKEN` | Agent Builder | (none) | Dead stub |
| `QUICKBOOKS_REALM_ID` | Agent Builder | (none) | Dead stub |
| `API_KEY` | Orchestration API | `""` | API auth key |
| `SKIP_AUTH` | Orchestration API | `true` | |
| `ENV` | Orchestration tracing | `dev` | |
| `COORD_TRACE` | Orchestration | (none) | Debug flag |
| `SKIP_MULTIAGENT_EVALS` | Orchestration | (none) | |
| `CE_DEBUG` | Agent Builder demo | (none) | Debug flag |
| `GEMINI_API_KEY` | Agent Builder .env.example | (none) | Alias — actual .env uses GOOGLE_API_KEY |

### 2.4 Docker/Postgres Configuration

| Key | Used In | Current Value | Notes |
|-----|---------|---------------|-------|
| `POSTGRES_DB` | docker-compose.yml | `ce_platform` (hardcoded) | Needs `${POSTGRES_DB}` |
| `POSTGRES_USER` | docker-compose.yml | `ce` (hardcoded) | Needs `${POSTGRES_USER}` |
| `POSTGRES_PASSWORD` | docker-compose.yml | `ce_local` (hardcoded) | Needs `${POSTGRES_PASSWORD}` |
| `POSTGRES_HOST` | (new) | - | For URL construction |
| `POSTGRES_PORT` | (new) | - | For URL construction |

---

## 3. All Call Sites Needing Migration

### 3.1 `load_dotenv()` Calls to Replace

| # | File | Line | Current | Migration |
|---|------|------|---------|-----------|
| 1 | `CE - Agent Builder/src/csuite/main.py` | 25 | `load_dotenv()` | `from ce_shared.env import find_and_load_dotenv; find_and_load_dotenv()` |
| 2 | `CE - Multi-Agent Orchestration/api/server.py` | 17 | `load_dotenv()` | Same |
| 3 | `CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py` | 39-40 | `from dotenv import load_dotenv; load_dotenv()` | Same |
| 4 | `CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/orchestrator.py` | 18-19 | `from dotenv import load_dotenv; load_dotenv()` | Same |
| 5 | `CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/team_assignment.py` | 9-10 | `from dotenv import load_dotenv; load_dotenv()` | Same |
| 6 | `CE - Agent Builder/scripts/notion_databases.py` | 27,31 | `from dotenv import load_dotenv; load_dotenv()` | Same (scripts) |
| 7 | `CE - Agent Builder/scripts/upsert_dfw_knowledge.py` | 20,22 | Same | Same (scripts) |
| 8 | `CE - Agent Builder/scripts/import_to_notion.py` | 16,19 | Same | Same (scripts) |
| 9 | `CE - Agent Builder/demo/app.py` | 33,56 | Same | Same (demo) |

### 3.2 Pydantic-Settings `env_file` to Update

| # | File | Line | Current | Migration |
|---|------|------|---------|-----------|
| 1 | `CE - Agent Builder/src/csuite/config.py` | 21 | `env_file=".env"` | Remove `env_file` — rely on env vars loaded by `find_and_load_dotenv()` |
| 2 | `CE - Evals/src/ce_evals/config.py` | 23 | `"env_file": ".env"` | Same — remove `env_file` |

### 3.3 Hardcoded Fallback URLs to Remove

| # | File | Line | Current | Migration |
|---|------|------|---------|-----------|
| 1 | `ce-db/src/ce_db/engine.py` | 10-13 | `os.environ.get("DATABASE_URL", "postgresql+asyncpg://ce:ce_local@localhost:5432/ce_platform")` | Construct from individual POSTGRES_* vars, no hardcoded fallback |

### 3.4 docker-compose.yml Hardcoded Values

| # | Line | Current | Migration |
|---|------|---------|-----------|
| 1 | 5 | `POSTGRES_DB: ce_platform` | `POSTGRES_DB: ${POSTGRES_DB:-ce_platform}` |
| 2 | 6 | `POSTGRES_USER: ce` | `POSTGRES_USER: ${POSTGRES_USER:-ce}` |
| 3 | 7 | `POSTGRES_PASSWORD: ce_local` | `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` (no default for passwords) |
| 4 | 28 | `MB_DB_DBNAME: metabase` | Keep as-is (metabase DB name is separate) |
| 5 | 30 | `MB_DB_USER: ce` | `MB_DB_USER: ${POSTGRES_USER:-ce}` |
| 6 | 31 | `MB_DB_PASS: ce_local` | `MB_DB_PASS: ${POSTGRES_PASSWORD}` |

---

## 4. Risk Areas and Gotchas

### R-1: Two Different ANTHROPIC_API_KEY Values
Agent Builder and Orchestration currently use **different API keys**. The consolidated root `.env` needs to pick one. Verify which key is active/valid before deleting per-project files.

### R-2: `LANGFUSE_HOST` vs `LANGFUSE_BASE_URL` Naming
Root `.env.example` uses `LANGFUSE_HOST` but Orchestration `.env` uses `LANGFUSE_BASE_URL`. The tracing code checks both (`os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")`). The consolidated `.env` should standardize on one name. Recommend `LANGFUSE_BASE_URL` since that matches the Langfuse SDK v3 convention.

### R-3: `NOTION_TOKEN` vs `NOTION_API_KEY` Naming
Root `.env.example` uses `NOTION_TOKEN` but Agent Builder uses `NOTION_API_KEY`. Need to pick one and update all references.

### R-4: `GEMINI_API_KEY` vs `GOOGLE_API_KEY`
Agent Builder `.env.example` lists `GEMINI_API_KEY` but actual `.env` uses `GOOGLE_API_KEY`. Orchestration tool_executor reads `GEMINI_API_KEY`. Both may need to exist in root `.env`, or code should standardize.

### R-5: pydantic-settings `env_file` Removal Timing
If `find_and_load_dotenv()` runs *before* Settings() is instantiated, pydantic-settings will find values in `os.environ` and `env_file` becomes unnecessary. But if `env_file` is removed and the loader hasn't run yet (e.g., direct import of config module), Settings() will fail. The migration must ensure loader runs before any Settings instantiation.

### R-6: `lru_cache` on `get_settings()` in Agent Builder
`config.py` uses `@lru_cache(maxsize=1)` on `get_settings()`. If `find_and_load_dotenv()` is called after the first `get_settings()` call (shouldn't happen, but guard against it), cached settings won't reflect loaded values. The loader must run before any import triggers the cache.

### R-7: Module-Level Side Effects in langfuse_tracing.py
`langfuse_tracing.py` calls `load_dotenv()` at module import time (line 39-40) and immediately reads env vars to initialize the Langfuse client (lines 47-49). The replacement `find_and_load_dotenv()` must also happen at import time or the Langfuse client will see empty env vars.

### R-8: Scripts That Depend on CWD
Scripts in `CE - Agent Builder/scripts/` call `load_dotenv()` without path args. They're typically run from the project root (`cd "CE - Agent Builder" && python scripts/foo.py`). After migration, `find_and_load_dotenv()` must find the monorepo root `.env` regardless of which project directory is CWD.

### R-9: ce-Evals Has No ce-shared Dependency Yet
`CE - Evals/pyproject.toml` does not list ce-shared. It needs `ce-shared @ file:../ce-shared` added to dependencies. It also has no `load_dotenv()` call anywhere — it relies on pydantic-settings `env_file=".env"` alone.

### R-10: ce-db Has No load_dotenv and No ce-shared
`ce-db` reads `DATABASE_URL` raw from `os.environ` with a hardcoded fallback. It has no dotenv dependency. Per the context decisions, ce-db should use ce-shared's loader and construct DATABASE_URL from individual POSTGRES_* vars.

### R-11: QuickBooks Keys Are Dead Code
`QUICKBOOKS_*` keys in Agent Builder's `.env.example` correspond to a dead stub (`quickbooks_mcp.py`). Include in root `.env.example` as optional/commented-out, don't make them required.

---

## 5. Validation Architecture

### 5.1 KEY_REGISTRY Design

```python
# Proposed structure for ce_shared/env.py

@dataclass
class KeyMeta:
    name: str                    # e.g., "ANTHROPIC_API_KEY"
    required_by: list[str]       # e.g., ["agent-builder", "orchestration", "evals"]
    category: str                # e.g., "llm", "observability", "storage", "search", "integration"
    description: str             # Human-readable purpose
    required: bool = True        # False = optional (warn only)

KEY_REGISTRY: dict[str, KeyMeta] = {
    "ANTHROPIC_API_KEY": KeyMeta(..., required=True),
    "PINECONE_API_KEY": KeyMeta(..., required=False),
    ...
}
```

### 5.2 Validation Flow

1. `find_and_load_dotenv()` called at startup
2. Walk up from CWD via `pathlib.Path.parents` looking for `.env` with a sentinel (e.g., check for `ce-shared/` sibling to confirm monorepo root)
3. Call `python-dotenv.load_dotenv(dotenv_path, override=False)` — shell exports take precedence
4. Run validation: iterate KEY_REGISTRY, check `os.environ` for each key
5. Required key missing → raise `EnvironmentError` with actionable message
6. Optional key missing → `logging.warning()`
7. Return the path that was loaded (for diagnostic reporting)

### 5.3 Nyquist Validation Points

For downstream validation (the "Nyquist" pattern — validate at sampling boundaries):

- **Startup boundary**: `find_and_load_dotenv()` validates all registry keys
- **Service boundary**: Individual tools/clients should still check their specific key before use (graceful degradation for optional keys like Pinecone, Notion)
- **Docker boundary**: `docker compose config` can validate variable interpolation before `docker compose up`
- **Diagnostic boundary**: `python -m ce_shared.env_check` provides on-demand full audit

### 5.4 env_check Module

```
$ python -m ce_shared.env_check

╭─ CE-AGENTS Environment Health ──────────────────────────╮
│ Loaded: /Users/scottewalt/Documents/CE - AGENTS/.env     │
╰──────────────────────────────────────────────────────────╯

Agent Builder Keys:
  ✓ ANTHROPIC_API_KEY    sk-ant-***FQAA    Required
  ✓ PINECONE_API_KEY     P_ym***o9mQ       Optional
  ✗ GITHUB_TOKEN         (not set)          Optional
  ...

⚠ Stale .env found: CE - Agent Builder/.env — should be deleted
```

---

## 6. Dependency Order

### Build Sequence

```
Step 1: ce-shared/src/ce_shared/env.py
        ├── find_and_load_dotenv()
        ├── KEY_REGISTRY
        └── validate_env()
        + Update ce-shared/pyproject.toml (add python-dotenv, rich deps)
        + Update ce-shared/__init__.py exports

Step 2: Root .env and .env.example
        ├── Create consolidated root .env (merge all 3 project .env files)
        ├── Create comprehensive .env.example
        └── Standardize key names (LANGFUSE_BASE_URL, NOTION_API_KEY, etc.)

Step 3: docker-compose.yml
        └── Replace hardcoded values with ${VAR} interpolation

Step 4: ce-db migration
        ├── Add ce-shared dependency to ce-db/pyproject.toml
        ├── Update engine.py to construct DATABASE_URL from POSTGRES_* vars
        └── Remove hardcoded fallback

Step 5: Migrate load_dotenv() call sites (project by project)
        ├── CE - Agent Builder (main.py, config.py, demo/app.py, scripts/*)
        ├── CE - Multi-Agent Orchestration (langfuse_tracing.py, api/server.py, airport pipeline)
        └── CE - Evals (config.py + add ce-shared dependency)

Step 6: Delete per-project .env files
        ├── CE - Agent Builder/.env
        ├── CE - Multi-Agent Orchestration/.env
        └── CE - Evals/.env

Step 7: env_check diagnostic
        └── ce_shared/env_check.py (__main__ entry point)

Step 8: Verification
        ├── Run each project's CLI from its own directory — confirm root .env loads
        ├── Run from monorepo root — confirm root .env loads
        ├── Remove a required key — confirm immediate failure with clear message
        ├── Run python -m ce_shared.env_check — confirm report
        └── docker compose config — confirm variable interpolation
```

### Why This Order

- Step 1 first: All subsequent steps depend on the loader existing
- Step 2 before Step 5: The root `.env` must exist before we can delete project `.env` files and before migrated code tries to load it
- Step 3 can run in parallel with Steps 4-5 (independent)
- Step 4 before Step 5: ce-db is imported by Orchestration's persistence layer; if ce-db changes its env loading, Orchestration must already have the new root `.env` available
- Step 6 after Step 5: Only delete old files after all code is migrated
- Step 7 after Step 6: env_check should detect stale files, so test after deletion to verify clean state
- Step 8 last: End-to-end verification

---

## 7. File Inventory for Plans

### Files to Create
- `ce-shared/src/ce_shared/env.py` — loader + registry + validation
- `ce-shared/src/ce_shared/env_check.py` — diagnostic CLI (`__main__` entry point)
- `ce-shared/src/ce_shared/__main__.py` — if needed for `python -m ce_shared.env_check`
- Root `.env` — consolidated from 3 project .env files
- Root `.env.example` — comprehensive rewrite

### Files to Modify
- `ce-shared/pyproject.toml` — add python-dotenv, rich dependencies
- `ce-shared/src/ce_shared/__init__.py` — export env module
- `docker-compose.yml` — variable interpolation
- `ce-db/src/ce_db/engine.py` — construct URL from vars
- `ce-db/pyproject.toml` — add ce-shared dependency
- `CE - Agent Builder/src/csuite/main.py` — replace load_dotenv
- `CE - Agent Builder/src/csuite/config.py` — remove env_file, add loader call
- `CE - Agent Builder/demo/app.py` — replace load_dotenv
- `CE - Agent Builder/scripts/notion_databases.py` — replace load_dotenv
- `CE - Agent Builder/scripts/upsert_dfw_knowledge.py` — replace load_dotenv
- `CE - Agent Builder/scripts/import_to_notion.py` — replace load_dotenv
- `CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py` — replace load_dotenv
- `CE - Multi-Agent Orchestration/api/server.py` — replace load_dotenv
- `CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/orchestrator.py` — replace load_dotenv
- `CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/team_assignment.py` — replace load_dotenv
- `CE - Evals/src/ce_evals/config.py` — remove env_file, add loader
- `CE - Evals/pyproject.toml` — add ce-shared dependency

### Files to Delete
- `CE - Agent Builder/.env`
- `CE - Multi-Agent Orchestration/.env`
- `CE - Evals/.env`
- `CE - Agent Builder/.env.example` (replaced by root)
- `CE - Multi-Agent Orchestration/.env.example` (replaced by root)
- `CE - Agent Builder/demo/.env.example` (replaced by root)

---

## RESEARCH COMPLETE
