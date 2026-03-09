# Research Summary

Synthesis of stack, features, architecture, and pitfalls research for the CE-AGENTS critical debt remediation: centralizing env vars, unifying pricing, fixing token estimation, and creating a shared utility module.

---

## Key Findings

### Stack

1. **uv workspaces (>=0.10.x) is the recommended monorepo package manager.** Industry standard for Python monorepos in 2026. Reads existing pyproject.toml and requirements.txt. Migration is additive -- existing hatchling build configs remain untouched.
2. **pydantic-settings (>=2.13.1) for centralized env loading.** Already a dependency in both Agent Builder and Orchestration. Supports typed validation, multi-env-file precedence, and structured defaults. No new dependencies.
3. **Anthropic pricing is wrong in both projects.** Orchestration has Opus at $15/$75 (3x too high, legacy pricing). Agent Builder has Haiku at $1/$5 (old pricing). Neither project is fully correct. Verified current rates: Opus $5/$25, Haiku $0.80/$4.00.
4. **`ce-db` already proves the cross-project import pattern.** It uses `file:` references in pyproject.toml/requirements.txt with a proper src-layout package. The new `ce-shared` package should follow this exact pattern.
5. **Admin API can verify pricing against actual billing.** `cost_report` + `usage_report` endpoints allow back-calculating effective per-token prices to detect drift. Requires Admin API key provisioning.

### Features

| Category | Table Stakes | Differentiators |
|----------|-------------|-----------------|
| **Env Management** | Single root `.env`, `.env.example` with all vars documented, startup validation, no secrets in docker-compose | Per-environment `.env` layering, startup env report (which file loaded), env validation CLI command |
| **Cost Tracking** | Back-calculate tokens from `total_cost_usd`, carry SDK cost as authoritative field, flag estimated vs actual tokens, graceful fallback for unknown models | Input/output ratio heuristic, SDK-vs-calculated cost reconciliation, per-turn cost attribution, budget guardrails |
| **Shared Pricing** | Single importable pricing module, exact model ID + substring fallback, date-stamped "last verified" field, consolidated cache/batch multipliers | Pricing verification script, model alias resolution, pricing as config file (TOML/JSON) instead of Python dict |

**Anti-features (deliberately not building):** secrets manager integration, dynamic runtime pricing fetch, tiktoken-based token counting, centralized config microservice, per-request pricing lookups.

### Architecture

**Proposed structure:**

```
CE - AGENTS/
  .env                            # Single source of truth for all API keys
  ce-shared/                      # New shared utilities package (parallels ce-db/)
    pyproject.toml                # setuptools, src layout, zero external deps
    src/ce_shared/
      __init__.py
      pricing.py                  # Unified MODEL_PRICING dict
      env.py                      # load_repo_env() -- finds root .env via .git/ marker
      models.py                   # Shared model ID constants
  ce-db/                          # Existing (unchanged)
  CE - Agent Builder/             # Adds ce-shared as file: dependency
  CE - Multi-Agent Orchestration/ # Adds ce-shared as file: dependency
  CE - Evals/                     # Adds ce-shared as file: dependency
```

**Dependency flow (top to bottom):**
- Application layer: Agent Builder, Orchestration, Evals
- Shared layer: ce-shared (pricing, env, constants)
- Data layer: ce-db (models, sessions, migrations)

**Build order (5 phases):**

1. **Create `ce-shared` package** -- zero risk, no existing code modified
2. **Wire `ce-shared` into consumers** -- add `file:` dependency to each project
3. **Migrate to shared imports** -- replace local pricing dicts and `load_dotenv()` calls
4. **Remove `sys.path` hack** -- add `csuite` as optional dep in Orchestration
5. **Clean up dead code** -- delete empty `Shared/`, orphan `.env` files, inline pricing constants

### Pitfalls

| ID | Risk | Severity | Phase |
|----|------|----------|-------|
| **P-1** | `load_dotenv()` resolves relative to CWD, not file location -- orphan `.env` files silently shadow the centralized one | Critical | Phase 1 |
| **P-2** | Existing `sys.path` hack in `agent_provider.py` conflicts with proper package imports -- can load two different versions of the same module | Critical | Phase 2 |
| **P-3** | Token back-calculation amplifies pricing errors -- 3x wrong pricing = 3x wrong token estimates in Langfuse | Critical | Phase 3 |
| **P-4** | Shared module creates deployment ordering dependency across venvs -- must use editable installs | High | Phase 2 |
| **G-2** | SDK `total_cost_usd` may include nested tool/sub-agent costs, inflating token estimates | Medium | Phase 3 |
| **G-4** | Directory names with spaces break `pip install` in Makefiles, some CI runners, and `subprocess.run(shell=True)` | Medium | Phase 4 |
| **G-6** | Haiku pricing discrepancy ($1/$5 vs $0.80/$4) affects more calls than Opus since Haiku is the orchestration model | High | Phase 2 |

---

## Recommendations

### Immediate (Phase 1-2, this sprint)

1. **Create `ce-shared` package with verified pricing.** Use the `ce-db` pattern (src layout, `file:` references). Verified prices: Opus $5/$25, Sonnet $3/$15, Haiku $0.80/$4.00. This single change fixes C-4 (pricing discrepancy) across both projects.

2. **Consolidate to a single root `.env`.** Delete all project-level `.env` files. Change every `load_dotenv()` call to use an absolute path computed from `__file__`. Update pydantic-settings `env_file` to absolute path. This fixes C-1 (duplicate env vars).

3. **Use editable installs for `ce-shared`.** Both venvs must `pip install -e ../ce-shared` so file changes propagate immediately. Add a `make update-all` script that installs in all venvs.

### Near-term (Phase 3-4, next sprint)

4. **Implement token back-calculation using shared pricing.** Back-calculate from `total_cost_usd`, flag all estimates with `token_source: "estimated_from_cost"`, and log both raw cost and estimated tokens. This fixes C-3.

5. **Replace `sys.path` hack with proper `file:` dependency.** Add `csuite @ file:../CE - Agent Builder` as optional dep in Orchestration. Test the spaces-in-path edge case; fall back to symlink if needed.

6. **Add cost reconciliation logging.** Log SDK-reported cost alongside price-table-calculated cost. Divergence signals a pricing table update is needed -- self-correcting mechanism for future drift.

### Strategic (Phase 5+, backlog)

7. **Evaluate uv workspace migration.** uv workspaces would give a single lockfile and eliminate `file:` reference management. Defer until the `ce-shared` pattern is proven with plain pip.

8. **Set up Admin API pricing verification.** Weekly cron or CI step that pulls billing data and compares against `ce_shared/pricing.py`. Alert if drift exceeds 5%.

9. **Add budget guardrails.** Per-protocol cost ceiling with warn/halt behavior. Prevents runaway agent loops.

---

## Open Questions

1. **Does `pip install` handle `file:` references with spaces in directory names?** The path `../CE - Agent Builder` contains spaces. `ce-db` works because its path has no spaces. Must test before Phase 4, or plan for a symlink workaround.

2. **Does the SDK's `total_cost_usd` include nested tool execution costs?** If an agent's tool call invokes another LLM (sub-agent or MCP server), the back-calculated token count will be inflated. Needs empirical testing with a known prompt.

3. **Should the shared pricing module store prices in Python dicts or a config file (TOML/JSON)?** Python dicts are simpler and type-checkable. Config files allow non-developer updates. Current recommendation: start with Python dicts, migrate to config file if pricing update frequency warrants it.

4. **Admin API key provisioning.** Pricing verification requires an Admin API key (`sk-ant-admin...`). Is one provisioned? If not, what is the process and timeline?

5. **uv migration timing.** STACK.md recommends uv workspaces. ARCHITECTURE.md recommends deferring to plain `file:` references first. When is the right time to make the switch -- after Phase 2, or after the full 5-phase plan is complete?

---

*Synthesized: 2026-03-09 | Sources: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
