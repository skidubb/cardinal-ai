# Architecture Research: Shared Utility Code in a Python Monorepo with Separate Venvs

## Current Architecture

### Sub-Project Layout

The monorepo has three application sub-projects plus one shared package:

| Sub-Project | Package Name | Build System | Install Method |
|-------------|-------------|-------------|----------------|
| `CE - Agent Builder/` | `csuite` | hatchling | `pip install -e ".[dev]"` |
| `CE - Multi-Agent Orchestration/` | (no package) | requirements.txt only | `pip install -r requirements.txt` |
| `CE - Evals/` | `ce-evals` | setuptools | `pip install -e .` |
| `ce-db/` | `ce-db` | setuptools | `pip install -e .` (via deps) |

Each application sub-project has its own venv. The `ce-db` shared package is already consumed via `file:` references in both `CE - Multi-Agent Orchestration/requirements.txt` and `CE - Evals/pyproject.toml`.

### Current Cross-Project Import Mechanisms

1. **`ce-db` (working pattern)**: A proper `src`-layout Python package at `ce-db/` with `pyproject.toml`. Both Orchestration and Evals declare it as a dependency via `ce-db @ file:../ce-db`. Each project's venv installs it in editable/linked mode. This is the correct pattern.

2. **Agent Builder -> Orchestration (broken pattern)**: `agent_provider.py` dynamically inserts `CE - Agent Builder/src` into `sys.path` at runtime (lines 84-87). This is fragile -- it depends on relative directory layout, breaks if directory names change, and bypasses dependency resolution entirely. Documented as concern I-10 in CONCERNS.md.

3. **Pricing constants (no sharing)**: Two independent pricing dictionaries exist with different values. `CE - Agent Builder/src/csuite/tools/cost_tracker.py` has Opus at $5/$25/MTok. `CE - Multi-Agent Orchestration/protocols/cost_tracker.py` has Opus at $15/$75/MTok. A 3x discrepancy (concern C-4).

4. **Env loading (no sharing)**: Each project calls `load_dotenv()` independently, loading from its own `.env` file. Duplicate keys across three `.env` files (concern C-1).

### What `Shared/` Was Supposed to Be

An empty `Shared/` directory exists at the repo root (concern I-4). It was presumably intended for cross-project code but was never populated.

## Proposed Changes

### Component 1: `ce-shared` -- Shared Utilities Package

- **Boundary**: Owns pricing tables, env loading, and any future cross-project constants (model IDs, common Pydantic models). Does NOT own business logic, agent code, or protocol code.
- **Interfaces**: Standard Python package import. All sub-projects declare it as a dependency via `file:` reference in their `pyproject.toml` or `requirements.txt`.
- **Location**: `ce-shared/` at repo root (parallel to `ce-db/`). NOT inside the empty `Shared/` directory (which has a space-free name but no package structure).

```
ce-shared/
  pyproject.toml          # setuptools, src layout, zero external deps
  src/
    ce_shared/
      __init__.py
      pricing.py           # Single source of truth for model pricing
      env.py               # Centralized env loading (finds repo root .env)
      models.py            # Shared model ID constants
```

**Key design decisions:**

1. **`src` layout** (matching `ce-db`). This prevents accidental imports from the project root and is the established pattern in this repo.

2. **Zero external dependencies**. `ce-shared` should depend on nothing (or at most `python-dotenv` for env loading). This avoids circular dependency issues and keeps it fast to install.

3. **`file:` reference from every consumer**. Each project adds `ce-shared @ file:../ce-shared` to its dependencies. When a developer runs `pip install -e .` or `pip install -r requirements.txt` in any project's venv, `ce-shared` gets installed as an editable package in that venv. No `sys.path` hacks needed.

### Component 2: `pricing.py` -- Unified Pricing Table

- **Boundary**: Owns all LLM pricing constants. Exports a `price_for_model(model_id: str) -> dict[str, float]` function and the raw pricing dict.
- **Interfaces**: `from ce_shared.pricing import price_for_model, MODEL_PRICING, CACHE_READ_MULTIPLIER`
- **Consumers**: Agent Builder's `CostTracker`, Orchestration's `ProtocolCostTracker`, any future cost analysis tooling.

The Orchestration cost tracker's `_price_for_model()` function (with substring fallback logic) is the better implementation -- adopt that pattern with verified pricing.

### Component 3: `env.py` -- Centralized Env Loading

- **Boundary**: Owns the logic for finding and loading the repo-root `.env` file. Does NOT own project-specific config (that stays in each project's `config.py` / `Settings` class).
- **Interfaces**: `from ce_shared.env import load_repo_env` -- walks up from `__file__` to find the repo root (by looking for `.git/`), then loads `{repo_root}/.env`.
- **Consumers**: Each project's entry point calls `load_repo_env()` instead of `load_dotenv()`. Project-specific overrides can still be loaded after.

This replaces three separate `.env` files with one at the repo root. Projects that need local overrides (rare) can still have a project-level `.env` loaded second -- `python-dotenv` respects `override=True/False`.

### Component 4: Refactored Agent Provider (no sys.path)

- **Boundary**: `agent_provider.py` in Orchestration continues to own the AgentBridge adapter pattern. But instead of `sys.path` manipulation, it imports `csuite` as a normal package dependency.
- **Interfaces**: No change to `AgentBridge` or `build_production_agents()` API.
- **Prerequisite**: Orchestration must add `csuite @ file:../../CE - Agent Builder` (or use a workspace-aware approach) as an optional dependency. The `file:` reference with spaces in the path works with pip but should be tested.

**Alternative if spaces cause issues**: Symlink `ce-agent-builder -> "CE - Agent Builder"` at the repo root, then reference `csuite @ file:../ce-agent-builder`. Or rename the directory (breaking change, but solves M-1 permanently).

## Data Flow

```
                  ce-shared (pricing.py, env.py)
                 /          |              \
                /           |               \
    CE - Agent Builder   CE - Multi-Agent    CE - Evals
    (csuite package)     Orchestration       (ce-evals package)
         |                   |                    |
         |                   |                    |
         +------- ce-db -----+--------------------+
                (database layer)
```

**Import direction** (dependencies flow downward):

```
Application layer:  Agent Builder, Orchestration, Evals
                         |              |            |
                         v              v            v
Shared layer:       ce-shared (pricing, env, constants)
                         |              |            |
                         v              v            v
Data layer:              ce-db (models, sessions, migrations)
```

**Pricing data flow after change:**

1. `ce-shared/src/ce_shared/pricing.py` defines `MODEL_PRICING` dict (single source of truth)
2. Agent Builder's `cost_tracker.py` imports `from ce_shared.pricing import MODEL_PRICING, price_for_model`
3. Orchestration's `cost_tracker.py` imports the same
4. Both compute costs identically -- no drift possible

**Env data flow after change:**

1. Repo root `.env` contains all API keys (one copy)
2. Each project's entry point calls `from ce_shared.env import load_repo_env; load_repo_env()`
3. `load_repo_env()` finds repo root via `.git/` marker, loads `{root}/.env`
4. Pydantic `Settings` classes in each project read from the now-populated `os.environ`

**Cross-project agent import flow after change:**

1. Orchestration's `requirements.txt` adds `csuite @ file:../CE - Agent Builder` as optional dep
2. `agent_provider.py` drops `sys.path` manipulation, does normal `from csuite.agents.sdk_agent import SdkAgent`
3. If `csuite` is not installed (e.g., CI without Agent Builder), the `ImportError` catch still works identically

## Build Order

Dependencies between components dictate implementation sequence:

### Phase 1: Create `ce-shared` package (no consumers yet)

1. Create `ce-shared/` directory with `pyproject.toml` and `src/ce_shared/` layout
2. Move/consolidate pricing constants into `ce_shared/pricing.py` with verified current Anthropic pricing
3. Implement `ce_shared/env.py` with repo-root `.env` discovery
4. Add model ID constants to `ce_shared/models.py`
5. **Test**: Install `ce-shared` in a scratch venv, verify imports work

**Risk**: Zero. No existing code is modified. New package sits alongside existing code.

### Phase 2: Wire `ce-shared` into consumers

6. Add `ce-shared @ file:../ce-shared` to Agent Builder's `pyproject.toml` dependencies
7. Add `ce-shared @ file:../ce-shared` to Orchestration's `requirements.txt`
8. Add `ce-shared @ file:../ce-shared` to Evals' `pyproject.toml` dependencies
9. Re-run `pip install -e .` (or `pip install -r requirements.txt`) in each project's venv

**Risk**: Low. Adding a dependency doesn't break anything. Existing code still uses local pricing/env.

### Phase 3: Migrate consumers to shared imports

10. Replace Agent Builder's `MODEL_PRICING` dict in `cost_tracker.py` with import from `ce_shared.pricing`
11. Replace Orchestration's `_PRICING` dict in `cost_tracker.py` with import from `ce_shared.pricing`
12. Replace `load_dotenv()` calls with `load_repo_env()` calls in entry points
13. Consolidate three `.env` files into one repo-root `.env`
14. **Test**: Run existing unit tests in all three projects. Run a protocol end-to-end.

**Risk**: Medium. Changing import paths and env loading could surface issues. Mitigate by keeping old `.env` files temporarily (with a deprecation comment) so nothing breaks if `load_repo_env()` has a bug.

### Phase 4: Clean up sys.path hack

15. Add `csuite @ file:../CE - Agent Builder` as optional dep in Orchestration's `requirements.txt`
16. Remove `sys.path` manipulation from `agent_provider.py`
17. Test production mode agent builds
18. **Test**: Run `python -m protocols.p06_triz.run -q "test" -a ceo cfo cto --mode production`

**Risk**: Medium-high. The `file:` reference with spaces in the path (`../CE - Agent Builder`) needs validation. If pip cannot handle it, fall back to a symlink approach or defer to a directory rename (M-1).

### Phase 5: Remove dead code

19. Delete empty `Shared/` directory
20. Remove duplicate `.env` files from sub-projects (after confirming repo-root `.env` works everywhere)
21. Remove inline pricing constants from both cost trackers (now imported)

**Risk**: Low. Cleanup only, no behavior change.

## Patterns for Cross-Project Imports (General Reference)

### Pattern A: `file:` references (recommended -- already used by ce-db)

```toml
# In pyproject.toml
[project]
dependencies = ["ce-shared @ file:../ce-shared"]

# In requirements.txt
ce-shared @ file:../ce-shared
```

Each project's venv gets the shared package installed via pip's local path resolution. Works with `pip install -e .` for editable installs. **This is the proven pattern in this repo** -- `ce-db` already uses it successfully.

### Pattern B: Python workspace tools (uv, hatch workspaces)

Tools like `uv` support workspace-level dependency resolution. A `pyproject.toml` at the repo root declares all sub-projects as workspace members. `uv sync` resolves everything in one pass. **Not recommended yet** -- would require migrating from pip to uv across all three projects simultaneously.

### Pattern C: Namespace packages

Use `ce_platform.pricing`, `ce_platform.db`, etc. as a unified namespace. **Over-engineered for this repo** -- the sub-projects are too different in scope and install requirements.

### Anti-patterns to avoid

- **`sys.path.insert()`**: Currently used in `agent_provider.py`. Fragile, bypasses dependency resolution, breaks with directory renames. Must be eliminated.
- **Symlinks in the repo**: Git handles symlinks inconsistently across platforms. Use only as a last resort for the spaces-in-directory-names issue.
- **Monorepo-wide single venv**: Would force all projects to share dependency versions. Not viable when Agent Builder uses hatchling and Orchestration uses requirements.txt with different dep trees.
- **Git submodules**: Adds complexity for no benefit when all code is in the same repo.
