---
phase: 2
plan: 4
status: complete
---
# Summary: Build env_check diagnostic CLI

## What was built
A Rich-formatted diagnostic CLI tool (`python -m ce_shared.env_check` or `python -m ce_shared`) that reports environment health across the monorepo. It shows which `.env` was loaded, all key statuses grouped by project with redacted values, color-coded status indicators, and warnings for stale per-project `.env` files.

## Key files
### Created
- ce-shared/src/ce_shared/env_check.py — Core module with `redact()`, `check_stale_envs()`, `group_keys_by_project()`, and `run_check()` functions
- ce-shared/src/ce_shared/__main__.py — Entry point enabling `python -m ce_shared` to run env_check
- ce-shared/tests/test_env_check.py — 10 unit tests covering redaction, stale detection, and grouping

### Modified
- None

## Decisions made
- Docker-category keys are grouped separately as "Docker / Database" rather than being filed under their `required_by` projects, keeping the output clean
- Deterministic group ordering: Agent Builder, Orchestration, Evals, Docker/Database
- `run_check()` catches EnvironmentError from `find_and_load_dotenv()` so missing required keys are reported in the table rather than crashing the diagnostic tool
- Monorepo root detection falls back to walking up from CWD if no .env was loaded (for stale file checks)

## Self-Check
PASSED — All 10 tests pass. `python -m ce_shared.env_check` produces formatted output with grouped key statuses, redacted values, and summary line.
