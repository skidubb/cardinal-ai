# Roadmap: CE-AGENTS Critical Debt Remediation

**Created:** 2026-03-09
**Granularity:** coarse
**Phases:** 3
**Requirements:** 28 mapped

## Phase 1: Shared Package & Pricing Unification

**Status:** In Progress (1/3 plans complete)

**Goal:** Create the `ce-shared` package with verified Anthropic pricing and migrate both cost trackers to use it, eliminating the 3x pricing discrepancy.
**Requirements:** SHPK-01, SHPK-02, SHPK-03, PRIC-01, PRIC-02, PRIC-03, PRIC-04, PRIC-05, PRIC-06, PRIC-07, PRIC-08

### Success Criteria
1. `from ce_shared.pricing import MODEL_PRICING` succeeds in both Agent Builder and Orchestration venvs
2. Running `csuite ceo "test"` and a protocol run both produce cost entries using Opus $5/$25, Sonnet $3/$15, Haiku $1/$5 pricing (verified against Anthropic docs 2026-03-09)
3. Changing a price in `ce-shared/src/ce_shared/pricing.py` is immediately reflected in both projects without reinstall (editable install)
4. No local pricing constants remain in either project's cost tracker files

## Phase 2: Environment Consolidation

**Goal:** Consolidate all API keys into a single root `.env`, make all projects load from it deterministically, and eliminate per-project `.env` files.
**Requirements:** ENVR-01, ENVR-02, ENVR-03, ENVR-04, ENVR-05, ENVR-06, ENVR-07, ENVR-08, ENVR-09

### Success Criteria
1. A single `.env` file at repo root is the only env file; no `.env` exists in any sub-project directory
2. Running any CLI command (`csuite`, protocol run, eval) from any CWD loads the root `.env` correctly
3. Removing a required key (e.g., `ANTHROPIC_API_KEY`) causes an immediate, descriptive error on startup — not a silent failure downstream
4. `python -m ce_shared.env_check` reports all key statuses across projects with redacted values
5. `docker-compose.yml` references `${POSTGRES_PASSWORD}` from root `.env` with no hardcoded credentials

## Phase 3: Token Estimation & Documentation

**Goal:** Back-calculate token counts from SDK cost data using shared pricing, add budget guardrails, and document the `bypassPermissions` design decision.
**Requirements:** TOKN-01, TOKN-02, TOKN-03, TOKN-04, TOKN-05, TOKN-06, DOCS-01, DOCS-02

### Success Criteria
1. SDK Agent turns report non-zero `input_tokens`/`output_tokens` values with `token_source: "estimated_from_cost"` metadata
2. Langfuse traces for protocol runs show token counts instead of 0 in generation spans
3. An unrecognized model string defaults to Opus-tier pricing for estimation (most conservative)
4. A protocol run exceeding a configured cost ceiling triggers a warning or halt (depending on config)
5. `CE - Agent Builder/docs/BYPASS_PERMISSIONS.md` exists with risk assessment, and `ce-shared/README.md` has usage examples

---

## Dependency Graph

```
Phase 1 (Shared Package + Pricing)
  └─► Phase 2 (Environment Consolidation)
  └─► Phase 3 (Token Estimation + Docs)
```

Phase 2 and Phase 3 both depend on Phase 1 (shared package must exist). Phases 2 and 3 are independent of each other and could be parallelized.

---
*Created: 2026-03-09*
