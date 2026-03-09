# Requirements: CE-AGENTS Critical Debt Remediation

**Defined:** 2026-03-09
**Core Value:** Cost tracking and pricing data across the monorepo must be accurate and consistent

## v1 Requirements

### Shared Package

- [ ] **SHPK-01**: `ce-shared` package exists at repo root with src layout, zero external dependencies
- [ ] **SHPK-02**: `ce-shared` is installable via `file:` reference from all three sub-projects
- [ ] **SHPK-03**: `ce-shared` uses editable installs so changes propagate without reinstall

### Pricing

- [ ] **PRIC-01**: Single `pricing.py` module contains all Anthropic model pricing (Opus $5/$25, Sonnet $3/$15, Haiku $0.80/$4.00 per MTok)
- [ ] **PRIC-02**: Pricing dict keyed by exact model ID with substring fallback matching
- [ ] **PRIC-03**: Each pricing entry includes a "last verified" date stamp
- [ ] **PRIC-04**: Cache read/write and batch discount multipliers consolidated in shared module
- [ ] **PRIC-05**: Centralized model alias map resolves shorthand ("opus") to canonical model ID ("claude-opus-4-6")
- [ ] **PRIC-06**: Pricing verification script compares local prices against actual billing data (requires Admin API key)
- [ ] **PRIC-07**: Agent Builder cost tracker imports pricing from `ce-shared` instead of local constants
- [ ] **PRIC-08**: Orchestration cost tracker imports pricing from `ce-shared` instead of local constants

### Environment

- [ ] **ENVR-01**: Single `.env` file at monorepo root contains all API keys
- [ ] **ENVR-02**: `.env.example` at root documents all required/optional vars with project usage notes
- [ ] **ENVR-03**: All `load_dotenv()` calls use absolute path computed from file location, not CWD
- [ ] **ENVR-04**: Pydantic Settings classes across all projects load from root `.env` via explicit path
- [ ] **ENVR-05**: Missing required keys cause immediate startup failure with clear error message
- [ ] **ENVR-06**: Docker-compose.yml references `${POSTGRES_PASSWORD}` from root `.env` instead of hardcoded value
- [ ] **ENVR-07**: Per-project `.env` files deleted after migration (no silent shadowing)
- [ ] **ENVR-08**: Startup env report logs which `.env` file loaded and which keys are set (redacted values)
- [ ] **ENVR-09**: Env validation CLI (`python -m ce_shared.env_check`) validates keys across all projects

### Token Estimation

- [ ] **TOKN-01**: SDK Agent back-calculates input/output token counts from `total_cost_usd` using shared pricing
- [ ] **TOKN-02**: SDK cost (`total_cost_usd`) is carried as the authoritative cost field
- [ ] **TOKN-03**: All estimated token counts are flagged with `token_source: "estimated_from_cost"`
- [ ] **TOKN-04**: Unknown model strings fall back to most expensive tier (Opus) for estimation
- [ ] **TOKN-05**: Cost reconciliation logs SDK-reported cost alongside price-table-calculated cost
- [ ] **TOKN-06**: Budget guardrails with configurable per-protocol cost ceiling (warn/halt behavior)

### Documentation

- [ ] **DOCS-01**: SDK Agent `bypassPermissions` usage documented as intentional design decision with risk assessment
- [ ] **DOCS-02**: `ce-shared` package has README with usage examples for both projects

## v2 Requirements

### Environment Enhancements

- **ENVR-10**: Per-environment `.env` layering (`.env.local` overrides for developer-specific settings)
- **ENVR-11**: Admin API key provisioning for automated pricing verification

### Cost Tracking Enhancements

- **TOKN-07**: Input/output ratio heuristic for more accurate token splitting
- **TOKN-08**: Per-turn cost attribution in multi-turn SDK sessions

### Infrastructure

- **INFR-01**: uv workspace migration for single lockfile and workspace-native dependency resolution
- **INFR-02**: Weekly CI step comparing pricing table against Admin API billing data

## Out of Scope

| Feature | Reason |
|---------|--------|
| Secrets manager integration (1Password, Vault) | Centralize first, encrypt later — per PROJECT.md |
| Dynamic runtime pricing from Anthropic | No public pricing API; static table with verification is more reliable |
| tiktoken-based token counting | SDK doesn't expose raw messages; `total_cost_usd` back-calculation is sufficient |
| Centralized config microservice | Overengineered for single-developer monorepo |
| `.env` encryption at rest | Files are gitignored on single machine; encryption adds key-management complexity |
| Removing `bypassPermissions` | Intentional for automation speed; document risk instead |
| Important/Minor CONCERNS.md items | Separate project |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SHPK-01 | 1 | Pending |
| SHPK-02 | 1 | Pending |
| SHPK-03 | 1 | Pending |
| PRIC-01 | 1 | Pending |
| PRIC-02 | 1 | Pending |
| PRIC-03 | 1 | Pending |
| PRIC-04 | 1 | Pending |
| PRIC-05 | 1 | Pending |
| PRIC-06 | 1 | Pending |
| PRIC-07 | 1 | Pending |
| PRIC-08 | 1 | Pending |
| ENVR-01 | 2 | Pending |
| ENVR-02 | 2 | Pending |
| ENVR-03 | 2 | Pending |
| ENVR-04 | 2 | Pending |
| ENVR-05 | 2 | Pending |
| ENVR-06 | 2 | Pending |
| ENVR-07 | 2 | Pending |
| ENVR-08 | 2 | Pending |
| ENVR-09 | 2 | Pending |
| TOKN-01 | 3 | Pending |
| TOKN-02 | 3 | Pending |
| TOKN-03 | 3 | Pending |
| TOKN-04 | 3 | Pending |
| TOKN-05 | 3 | Pending |
| TOKN-06 | 3 | Pending |
| DOCS-01 | 3 | Pending |
| DOCS-02 | 3 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28 ✓
- Unmapped: 0

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after roadmap creation*
