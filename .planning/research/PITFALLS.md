# Pitfalls Research: Python Monorepo Debt Remediation

Domain: Centralizing env vars, unifying pricing, fixing token estimation, and shared module versioning in the CE-AGENTS monorepo (Agent Builder + Multi-Agent Orchestration + Evals).

---

## Critical Pitfalls

### P-1. `load_dotenv()` Call Order Silently Overrides Centralized `.env`

- **Risk**: Both Agent Builder (`main.py:25`) and Orchestration (`langfuse_tracing.py:40`, `api/server.py:17`) call `load_dotenv()` with no explicit path, which resolves to `.env` relative to the *current working directory*. After centralizing to a root `.env`, if a developer runs `cd "CE - Agent Builder" && python -m csuite.main`, `load_dotenv()` loads `CE - Agent Builder/.env` (if it still exists) instead of the root. Pydantic-settings `env_file=".env"` in `config.py:21` has the same CWD-relative behavior. The system will appear to work but use stale or duplicate keys with no error.
- **Warning signs**: Tests pass in CI (which sets env vars directly) but fail locally. Cost reports show different totals depending on which directory you `cd` into. `LANGFUSE_SECRET_KEY` works from one project but not another.
- **Prevention**: (1) Delete project-level `.env` files entirely after migration -- do not leave empties or stubs. (2) Change all `load_dotenv()` calls to use an explicit path: `load_dotenv(Path(__file__).resolve().parents[N] / ".env")` pointing to the monorepo root. (3) Update pydantic-settings `env_file` to an absolute path computed at import time. (4) Add a startup assertion that checks for stray `.env` files in sub-project roots and warns.
- **Phase**: Env centralization (Phase 1). Must be addressed before any other work, since incorrect keys silently corrupt cost tracking data.

### P-2. Cross-Project Import via `sys.path` Manipulation Breaks When Shared Module is Introduced

- **Risk**: `agent_provider.py:84-87` dynamically inserts `CE - Agent Builder/src` into `sys.path`. If the shared pricing module is placed at the monorepo root (e.g., `shared/pricing.py`), the Orchestration project needs *another* `sys.path` entry or a proper package install. Each new shared module compounds the fragility. Worse: if Agent Builder is installed as a package (`pip install -e .`), importing `csuite.tools.cost_tracker` resolves differently than the `sys.path` hack, potentially loading two different versions of the pricing constants.
- **Warning signs**: `ImportError` for the shared module only in Orchestration (not Agent Builder). Or: pricing changes in the shared file are not picked up because `sys.path` resolves to a cached `.pyc` from the old path. `isinstance()` checks fail because the same class was loaded via two different import paths.
- **Prevention**: (1) Make the shared pricing module a proper installable package (even a single-file `shared/` package with `pyproject.toml`). Install it in editable mode in both project venvs. (2) Do NOT add more `sys.path` hacks. (3) Verify with `python -c "import shared.pricing; print(shared.pricing.__file__)"` from both project venvs to confirm they resolve to the same file.
- **Phase**: Shared pricing module (Phase 2). Design the import strategy before writing the module.

### P-3. Token Back-Calculation Produces Systematically Wrong Numbers When Pricing Is Wrong

- **Risk**: The SDK Agent (`sdk_agent.py:306-315`) will back-calculate tokens from `total_cost_usd` using pricing constants. If the pricing table has the wrong values (currently a 3x discrepancy between projects), the estimated token counts will be off by the same factor. Since token counts feed Langfuse generation spans and budget alerts, wrong pricing cascades into wrong observability data. Crucially, there is no way to validate the estimates against ground truth since the SDK does not expose tokens.
- **Warning signs**: Langfuse generation spans show implausibly low or high token counts. Cost-per-token ratios differ between Agent Builder runs and Orchestration runs by a constant factor. Budget alerts trigger (or fail to trigger) at unexpected thresholds.
- **Prevention**: (1) Verify pricing against Anthropic's actual billing page/API *before* implementing back-calculation -- do not trust either project's hardcoded values. (2) Log both the raw `total_cost_usd` from the SDK AND the estimated tokens, so downstream consumers can choose which to trust. (3) Add a metadata flag (`token_source: "estimated_from_cost"`) so Langfuse queries can filter estimated vs actual counts. (4) Cross-validate by running a known prompt through the direct API (which returns tokens) and the SDK (which returns cost) to calibrate.
- **Phase**: Token estimation (Phase 3). Must happen AFTER pricing is verified and unified (Phase 2).

### P-4. Shared Pricing Module Creates a Deployment Ordering Dependency

- **Risk**: Once both projects import from a shared pricing module, updating pricing requires a coordinated deploy: update the shared module, then reinstall in both venvs. If only one venv is updated (common when a developer is working in one project), the projects will silently use different prices -- the exact problem the shared module was supposed to fix.
- **Warning signs**: `pip list | grep shared` shows different versions in different venvs. Cost discrepancy reappears after a pricing update. Git blame shows pricing was updated but `pip install -e .` was not re-run.
- **Prevention**: (1) Use editable installs (`pip install -e .`) for the shared package in both venvs so file changes propagate immediately without reinstall. (2) Add a version constant in the shared module and have both projects log it at startup. (3) Include a `make update-all` or equivalent script that installs the shared package in all venvs atomically. (4) Consider a runtime assertion: at import time, the shared module checks if its `__file__` path is inside the monorepo root (not a cached site-packages copy).
- **Phase**: Shared pricing module (Phase 2). Build the update workflow before shipping the module.

---

## Common Mistakes

### M-1. Leaving Orphan `.env` Files That Shadow the Centralized One

After centralizing to a root `.env`, developers frequently leave the old project-level `.env` files "just in case." These become landmines: any `load_dotenv()` call without an explicit path will find them first. Even empty `.env` files can override values (an empty `ANTHROPIC_API_KEY=` line sets the var to empty string, overriding the root file's value).

- **Prevention**: Delete old `.env` files. Add them to a pre-commit check that fails if `.env` exists in sub-project roots. Update `.env.example` files to point to the root.
- **Phase**: Env centralization (Phase 1).

### M-2. Back-Calculating Tokens Without Accounting for Caching and Batch Discounts

The Agent Builder cost tracker already has `CACHE_READ_MULTIPLIER = 0.10` and `BATCH_DISCOUNT = 0.50`. If the SDK's `total_cost_usd` includes cached-read discounts or batch pricing, a naive `tokens = cost / price_per_token` will overcount or undercount tokens. The formula must account for the pricing tier that was actually applied.

- **Prevention**: Check if the SDK's cost includes cache/batch adjustments. If unknown, document the assumption explicitly and add a tolerance band to any assertion on token counts. Do not present estimated tokens with false precision (e.g., round to nearest 100).
- **Phase**: Token estimation (Phase 3).

### M-3. Substring Fallback Matching Produces Wrong Prices for New Model IDs

Both cost trackers use substring matching (`"opus" in model_lower`) as a fallback when exact model IDs are not found. This is fragile: a future model ID like `claude-opus-4-7-mini` would match "opus" pricing even if it has different rates. The Orchestration tracker's `_price_for_model()` iterates in a fixed order (`opus`, `sonnet`, `haiku`), so a model containing multiple substrings (hypothetical `claude-sonnet-opus-bridge`) would always match opus.

- **Prevention**: In the shared pricing module, use exact model ID matching only. Add an explicit `UNKNOWN_MODEL` fallback that logs a warning rather than silently applying opus rates. Keep the substring fallback only as a last resort with a loud log message.
- **Phase**: Shared pricing module (Phase 2).

### M-4. Circular Import When Orchestration Imports Shared Module That Imports Agent Builder

If the shared pricing module is placed inside Agent Builder's package tree (e.g., `csuite.shared.pricing`), Orchestration importing it via the `sys.path` hack triggers loading the entire `csuite` package, which may import modules with side effects (e.g., `load_dotenv()` in `main.py`). This creates hard-to-debug circular import chains.

- **Prevention**: The shared module must be an independent package with zero dependencies on either Agent Builder or Orchestration. No imports from `csuite.*` or `protocols.*` in the shared module.
- **Phase**: Shared pricing module (Phase 2).

---

## Gotchas

### G-1. Pydantic-Settings `env_file` Is Relative to CWD, Not to the Python File

`Settings` in `config.py` uses `env_file=".env"` which resolves relative to `os.getcwd()`, not relative to `config.py`'s location. This is a pydantic-settings design choice that surprises most developers. After centralization, if someone runs the CLI from a subdirectory, the `.env` will not be found and all optional fields will use defaults (silently).

- **Prevention**: Set `env_file` to an absolute path: `env_file=str(Path(__file__).resolve().parents[4] / ".env")` (adjust parent count for depth).

### G-2. The Claude Agent SDK `total_cost_usd` May Include Tool Execution Costs

The SDK wraps the entire agent turn including tool calls. If a tool call invokes another LLM (e.g., a sub-agent or an MCP server that calls Claude), the `total_cost_usd` may include those nested costs. Back-calculating tokens from this inflated cost using single-call pricing will overestimate tokens for the primary model.

- **Prevention**: Instrument a test run with known tool calls and compare the SDK cost to the expected cost of just the primary model's input/output. Document whether tool costs are included.

### G-3. `asyncio.gather()` Parallelism Means Cost Tracking Must Be Thread-Safe

Both cost trackers accumulate costs in mutable state (`list.append()` / dataclass fields). When `asyncio.gather()` dispatches multiple agents concurrently and each logs costs, the tracker must handle concurrent writes. Python's GIL protects `list.append()` for CPython but not for more complex operations like aggregation-on-write.

- **Prevention**: Use `asyncio.Lock` in any cost-tracking write path that does read-modify-write. Or accumulate costs in per-agent isolated trackers and merge at the end.

### G-4. Directory Names with Spaces Break `pip install -e .` in Some Shell Contexts

`CE - Agent Builder` and `CE - Multi-Agent Orchestration` contain spaces. Running `pip install -e "../../shared"` from inside these directories works in bash with quotes, but breaks in Makefiles (where quoting rules differ), in some CI runners, and in `subprocess.run()` calls that use `shell=True` with unquoted paths. The `sys.path` hack in `agent_provider.py:84` handles this correctly with `Path()` objects, but any new tooling must also handle it.

- **Prevention**: Always use `pathlib.Path` for cross-project path references. Never construct paths with string concatenation. Test the shared package install from each project directory before merging.

### G-5. Two Separate Venvs Mean `pip freeze` Divergence Is Inevitable

Even with a shared editable package, the two project venvs will drift in transitive dependencies over time. Agent Builder uses `hatchling` and Orchestration uses `requirements.txt`. A shared package that depends on, say, `pydantic>=2.0` might get `2.6` in one venv and `2.8` in another, causing subtle behavior differences.

- **Prevention**: Pin the shared package's dependencies tightly. Run `pip check` in both venvs in CI. Consider a `constraints.txt` at the monorepo root that both projects reference.

### G-6. Haiku Pricing Disagrees Between the Two Trackers

Often overlooked: the Opus 3x discrepancy ($5 vs $15) gets all the attention, but Haiku also disagrees: Agent Builder has $1.00/$5.00 while Orchestration has $0.80/$4.00. Since Haiku is the `orchestration_model` used for mechanical steps (the bulk of API calls by count), this smaller per-call discrepancy may actually produce a larger aggregate cost error than the Opus difference.

- **Prevention**: When verifying pricing, check ALL model tiers, not just the headline tier. The Haiku discrepancy is the higher-volume error.
