# Stack Research: Centralized Env, Shared Utilities, and Pricing Verification

Research for CE-AGENTS critical debt remediation. Covers three domains: centralizing environment variables, creating shared importable modules, and verifying/maintaining Anthropic API pricing.

---

## 1. Centralized Environment Variables

### Recommended Stack

#### pydantic-settings (>=2.13.1) -- Typed settings with multi-source loading

- **Confidence:** High
- **Rationale:** Already a dependency in both Agent Builder and Orchestration. Supports loading from multiple `.env` files with explicit precedence, typed validation, and `env_prefix` for namespace isolation. The monorepo already uses it in Agent Builder's `config.py`. Extending to a shared root config is a natural evolution, not a new dependency.
- **Alternative:** `python-dotenv` alone (already present) -- but lacks validation, type coercion, and structured defaults. Would require manual `os.getenv()` everywhere.

#### Pattern: Root `.env` with `env_file` chain in pydantic-settings

```
# Root pyproject.toml or shared config module
CE - AGENTS/
  .env                          # Single source of truth for all API keys
  shared/ce_shared/config.py    # BaseSettings subclass, env_file=[repo_root/.env]
  CE - Agent Builder/            # imports ce_shared.config, adds project-specific overrides
  CE - Multi-Agent Orchestration/ # imports ce_shared.config
  CE - Evals/                    # imports ce_shared.config
```

- **Confidence:** High
- **Rationale:** pydantic-settings v2 `model_config` supports `env_file` as a list with precedence (later files override earlier). Define one `CoreSettings` class in the shared package with all common keys (`ANTHROPIC_API_KEY`, `LANGFUSE_*`, `DATABASE_URL`, `PINECONE_API_KEY`). Each sub-project can subclass or compose with project-specific settings. Eliminates C-1 (duplicate keys across 3 `.env` files).
- **Key detail:** Use `env_file=[root_env_path]` computed from `Path(__file__).resolve()` relative traversal, NOT hardcoded absolute paths. The shared module knows its own location in the repo and can find the root `.env` reliably.

#### What NOT to do

- **Do NOT use `python-decouple`** -- adds a dependency with no advantage over pydantic-settings, which you already have.
- **Do NOT use per-project `.env` files** -- this is the current broken state. One root `.env`, period.
- **Do NOT use env_prefix namespacing** (e.g., `AB_ANTHROPIC_API_KEY`) -- over-engineering for a 3-project monorepo where the keys are genuinely shared. Prefixing only makes sense if projects need *different values* for the same key, which is not the case here.
- **Do NOT adopt 1Password CLI / Vault / AWS Secrets Manager yet** -- PROJECT.md explicitly scopes this out. Centralize first, encrypt later.

---

## 2. Shared Utility Module (Cross-Project Imports)

### Recommended Stack

#### uv workspaces (uv >=0.10.x) -- Monorepo package management

- **Confidence:** High
- **Rationale:** uv is the standard Python monorepo tool in 2025-2026. Latest release: v0.10.9 (March 6, 2026). Workspace support gives you a single lockfile, local `path` dependencies between packages, and fast installs (10-100x faster than pip). FOSDEM 2026 featured Apache Airflow shipping 120+ distributions from a single repo using uv workspaces. The Python ecosystem has converged on uv as the successor to pip/poetry/hatch for project management.
- **Alternative considered:** `pip install -e ../shared` with relative paths -- fragile, no lockfile coordination, breaks in CI. This is essentially what `sys.path.insert()` in `agent_provider.py` does today, and it is concern I-10.
- **Alternative considered:** Hatch workspaces -- Hatch has no workspace concept. It is a build backend, not a project manager. The codebase already uses hatchling as a *build backend*, which is compatible with uv as the *project manager*.
- **Migration path:** uv reads existing `pyproject.toml` and `requirements.txt` files. Add `[tool.uv.workspace]` to the root `pyproject.toml` and `[tool.uv.sources]` entries. Existing hatchling build configs remain untouched.

#### Shared package: `ce-shared` as a workspace member

```toml
# Root pyproject.toml (new or extended)
[tool.uv.workspace]
members = [
    "shared",
    "CE - Agent Builder",
    "CE - Multi-Agent Orchestration",
    "CE - Evals",
    "ce-db",
]

[tool.uv.sources]
ce-shared = { workspace = true }
```

```
shared/
  pyproject.toml         # name = "ce-shared", build-backend = "hatchling"
  ce_shared/
    __init__.py
    config.py            # CoreSettings(BaseSettings) -- centralized env loading
    pricing.py           # MODEL_PRICING dict -- single source of truth
    models.py            # Shared model IDs, tiers, constants
```

- **Confidence:** High
- **Rationale:** Each sub-project declares `ce-shared` as a dependency. uv resolves it from the workspace (local path). No `sys.path` hacks, no relative imports across project boundaries. Standard Python packaging -- `from ce_shared.pricing import MODEL_PRICING` works everywhere. Directly fixes concern I-10 (sys.path manipulation) and I-4 (empty `Shared/` directory).

#### What NOT to do

- **Do NOT keep using `sys.path.insert()`** -- fragile, invisible to type checkers and linters, breaks `pip install`. This is concern I-10 and must be eliminated.
- **Do NOT put shared code in the root as loose `.py` files** -- not importable as a package, invisible to dependency resolution.
- **Do NOT create a separate git repo for shared code** -- over-engineering. uv workspaces exist precisely for this use case.
- **Do NOT use `pip install -e ../path`** -- works locally but breaks in CI unless paths are carefully managed. uv workspaces handle this natively.
- **Do NOT rename directories to remove spaces yet** -- this is a separate concern (M-1). uv workspaces work with quoted paths. Tackle naming in a follow-up.

---

## 3. Anthropic API Pricing -- Verified Ground Truth

### Current Pricing (March 2026, verified via docs.anthropic.com)

| Model | Model ID | Input ($/MTok) | Output ($/MTok) |
|-------|----------|-----------------|------------------|
| Opus 4.6 | `claude-opus-4-6` | $5.00 | $25.00 |
| Sonnet 4.6 | `claude-sonnet-4-6` | $3.00 | $15.00 |
| Sonnet 4.5 | `claude-sonnet-4-5-20250929` | $3.00 | $15.00 |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | $0.80 | $4.00 |

**Additional pricing modifiers:**
- Batch API: 50% discount on both input and output
- Prompt cache write: 1.25x input price
- Prompt cache read (hit): 0.10x input price (90% savings)
- Long context (>200K input tokens): 2x standard rates -- Opus: $10/$50, Sonnet: $6/$22.50

### Assessment of Current Codebase Pricing

| Project | File | Opus Price | Status |
|---------|------|------------|--------|
| Agent Builder | `tools/cost_tracker.py` | $5/$25 | **CORRECT** (matches current Opus 4.6 pricing) |
| Orchestration | `protocols/cost_tracker.py` | $15/$75 | **WRONG** (this is legacy Opus 4.0/4.1 pricing, 3x too high) |

**Haiku discrepancy:**
- Agent Builder: $1.00/$5.00 -- **WRONG** (this is old Haiku pricing)
- Orchestration: $0.80/$4.00 -- **CORRECT** (matches current Haiku 4.5 pricing)

**Resolution:** The shared `ce_shared/pricing.py` must use the verified prices above. Neither project is fully correct today.

### Programmatic Pricing Verification

#### Anthropic Admin API -- Usage and Cost endpoints

- **Confidence:** Medium (requires Admin API key provisioning)
- **Endpoint:** `GET /v1/organizations/cost_report` -- returns actual billed costs in USD grouped by model, workspace, or description
- **Endpoint:** `GET /v1/organizations/usage_report/messages` -- returns token consumption broken down by model
- **Auth:** Requires Admin API key (`sk-ant-admin...`), not a regular API key. Only org admins can provision these via the Claude Console.
- **Rationale:** These endpoints report what Anthropic *actually charged*, not what your code *thinks* the price is. By comparing `cost_report` totals against `usage_report` token counts, you can back-calculate the effective per-token price and detect when your hardcoded constants have drifted.
- **Limitation:** No endpoint returns a "price list" directly. You infer prices from actual billing data. Data appears within ~5 minutes of API call completion.
- **Recommendation:** Build a periodic check (weekly cron or CI step) that pulls the last 7 days of cost/usage data, divides cost by tokens per model, and compares against `ce_shared/pricing.py` constants. Alert if drift exceeds 5%.

#### What NOT to do for pricing

- **Do NOT scrape the Anthropic pricing page** -- fragile, violates ToS, breaks when page structure changes.
- **Do NOT rely on LiteLLM's pricing data** -- LiteLLM maintains its own pricing dict that may lag behind actual Anthropic pricing changes. Use it as a cross-reference, not a source of truth.
- **Do NOT hardcode prices in two places** -- this is the current bug (C-4). One file, one import, both projects.

---

## Key Decisions

| Decision | Recommendation | Confidence | Rationale |
|----------|---------------|------------|-----------|
| Package manager | **uv** (>=0.10.x) | High | Industry standard for Python monorepos in 2026. Workspace support, single lockfile, reads existing pyproject.toml/requirements.txt. Migration is additive. |
| Shared package location | `shared/ce_shared/` as uv workspace member | High | Standard Python package, importable everywhere. Eliminates sys.path hacks. Empty `Shared/` dir already signals intent. |
| Build backend for shared pkg | **hatchling** | High | Already used by Agent Builder and MCP servers. Consistent across the monorepo. uv is the project manager; hatchling is the build backend. |
| Settings framework | **pydantic-settings** (>=2.13.1) | High | Already a dependency. Typed, validated, multi-env-file support. No new deps. |
| Env file strategy | Single root `.env`, no per-project `.env` files | High | Eliminates duplication (C-1). Shared settings class finds root `.env` via path traversal. |
| Pricing source of truth | `ce_shared/pricing.py` imported by both cost trackers | High | Single file, single update point. Directly fixes C-4. |
| Pricing verification | Anthropic Admin API (`cost_report` + `usage_report`) | Medium | Only way to verify against actual billing. Requires Admin API key setup. |
| Token estimation from cost | Back-calculate: `tokens = (total_cost_usd / price_per_token) * 1_000_000` | High | SDK provides `total_cost_usd` but not token counts. Using verified prices from `ce_shared/pricing.py` gives usable estimates. |

## Implementation Priority

1. **Create `shared/ce_shared/pricing.py`** -- immediate, fixes C-4, no tooling changes needed (can start with `sys.path` or `pip install -e` before uv migration)
2. **Create `shared/ce_shared/config.py`** -- immediate, fixes C-1
3. **Add uv workspace config** -- replaces sys.path hack (I-10), standardizes development workflow
4. **Set up Admin API pricing verification** -- requires admin key provisioning, lower urgency

---

## Versions Summary

| Tool/Library | Recommended Version | Current Latest | Notes |
|-------------|-------------------|----------------|-------|
| uv | >=0.10.0 | 0.10.9 (Mar 6, 2026) | Install via `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| pydantic-settings | >=2.13.0 | 2.13.1 (Feb 19, 2026) | Already a dependency, may need version bump |
| pydantic | >=2.0.0 | (already pinned) | No change needed |
| hatchling | (already pinned) | (already pinned) | Build backend for shared package |
| python-dotenv | >=1.0.0 | (already pinned) | Loaded by pydantic-settings internally |

---

*Last updated: 2026-03-09*
*Sources: Anthropic API docs, uv docs, pydantic-settings docs, PyPI, GitHub releases*
