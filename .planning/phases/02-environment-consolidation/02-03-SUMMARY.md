---
phase: 2
plan: 3
status: complete
---
# Summary: Migrate all load_dotenv call sites and pydantic-settings to ce-shared loader

## What was built
Replaced every `load_dotenv()` call and `env_file=".env"` reference across all 4 projects with `ce_shared.env.find_and_load_dotenv()`. This ensures all projects load environment variables from the single root `.env` regardless of CWD. Also migrated ce-db to construct DATABASE_URL from individual POSTGRES_* vars instead of using a hardcoded fallback.

## Key files
### Created
- (none)

### Modified
- CE - Agent Builder/src/csuite/main.py — replaced load_dotenv with find_and_load_dotenv(project="agent-builder")
- CE - Agent Builder/src/csuite/config.py — removed env_file=".env" from SettingsConfigDict, added env guard in get_settings()
- CE - Agent Builder/demo/app.py — replaced load_dotenv with find_and_load_dotenv(project="agent-builder")
- CE - Agent Builder/scripts/notion_databases.py — replaced load_dotenv with find_and_load_dotenv()
- CE - Agent Builder/scripts/upsert_dfw_knowledge.py — replaced load_dotenv with find_and_load_dotenv()
- CE - Agent Builder/scripts/import_to_notion.py — replaced load_dotenv with find_and_load_dotenv()
- CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py — replaced load_dotenv with find_and_load_dotenv(), kept dotenv fallback for graceful degradation
- CE - Multi-Agent Orchestration/api/server.py — replaced load_dotenv with find_and_load_dotenv()
- CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/orchestrator.py — replaced load_dotenv with find_and_load_dotenv()
- CE - Multi-Agent Orchestration/protocols/airport_5g_pipeline/team_assignment.py — replaced load_dotenv with find_and_load_dotenv()
- CE - Evals/pyproject.toml — added ce-shared dependency
- CE - Evals/src/ce_evals/config.py — removed env_file=".env", added find_and_load_dotenv guard in get_settings()
- ce-db/pyproject.toml — added ce-shared dependency
- ce-db/src/ce_db/engine.py — replaced hardcoded DATABASE_URL fallback with POSTGRES_* var construction

## Decisions made
- langfuse_tracing.py keeps a dotenv fallback (`except ImportError`) since it's designed for graceful degradation when ce-shared isn't installed
- config.py modules (Agent Builder + Evals) use `_env_loaded` flag to ensure find_and_load_dotenv() runs exactly once before Settings construction
- ce-db constructs DATABASE_URL from individual POSTGRES_* vars with no hardcoded password; DATABASE_URL env var is checked first as an override
- POSTGRES_USER defaults to "ce" and POSTGRES_DB defaults to "ce_platform" (matching docker-compose defaults), but POSTGRES_PASSWORD has no default (warns if missing)

## Self-Check
PASSED — All 4 verification checks pass:
1. No `from dotenv import load_dotenv` in migrated source (langfuse fallback is intentional)
2. No `env_file=".env"` in Agent Builder or Evals source
3. No hardcoded `ce_local` password in ce-db
4. `find_and_load_dotenv()` loads ANTHROPIC_API_KEY from root .env successfully
