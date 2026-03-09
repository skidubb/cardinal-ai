# Phase 01 Verification: Shared Package & Pricing Unification

**Verified:** 2026-03-09
**Verifier:** Claude Code (automated)
**Phase Status:** PARTIALLY COMPLETE -- 3 issues found

---

## Success Criteria (from ROADMAP.md)

### 1. `from ce_shared.pricing import MODEL_PRICING` succeeds in both venvs

**PASS**

Verified by running the import in both activated venvs:
- Agent Builder venv: `SUCCESS` -- returns `(5.0, 25.0)` for Opus
- Orchestration venv: `SUCCESS` -- returns `(5.0, 25.0)` for Opus

### 2. Cost entries use correct pricing (Opus $5/$25, Sonnet $3/$15, Haiku $1/$5)

**PASS**

- `ce-shared/src/ce_shared/pricing.py` defines `claude-opus-4-6` as `(5.00, 25.00)`
- `claude-sonnet-4-6` as `(3.00, 15.00)`
- `claude-haiku-4-5-20251001` as `(1.00, 5.00)`
- Agent Builder's `cost_tracker.py` imports `get_pricing` from ce-shared and delegates all lookups
- Orchestration's `cost_tracker.py` imports `cost_for_model` from ce-shared and delegates via thin wrapper
- 14 ce-shared unit tests pass confirming correct pricing math
- No stale pricing ($15/$75 Opus, $0.80/$4 Haiku) remains in either cost tracker

Note: Not verified via actual `csuite ceo "test"` or protocol run (would require API keys and real API calls). Verified structurally by code inspection.

### 3. Editable install -- changes propagate without reinstall

**FAIL**

ce-shared is installed as a **regular (non-editable)** install, not an editable install. Evidence:
- `pip show ce-shared` reports `Location: /Users/scottewalt/.pyenv/versions/3.13.11/lib/python3.13/site-packages`
- The `direct_url.json` shows `"dir_info": {}` (no `"editable": true` flag)
- Files in site-packages are copies, not symlinks to the source tree
- Both Agent Builder and Orchestration resolve to the same global site-packages copy

Changing a price in `ce-shared/src/ce_shared/pricing.py` will NOT be reflected until `pip install -e ../ce-shared` is re-run. This contradicts success criterion 3 and requirement SHPK-03.

**Fix required:** Reinstall with `pip install -e ../ce-shared` (the `-e` flag) in both venvs, or better, in the shared Python environment.

### 4. No local pricing constants in either cost tracker

**PASS**

- `CE - Agent Builder/src/csuite/tools/cost_tracker.py`: No local `MODEL_PRICING` dict, no local `ModelTier` enum, no local multiplier constants. All imported from `ce_shared.pricing`. The docstring mentions pricing values but only as documentation, not as code constants.
- `CE - Multi-Agent Orchestration/protocols/cost_tracker.py`: No local `_PRICING` dict, no local `_CACHE_READ_MULTIPLIER`, no local `_price_for_model`. All removed, replaced by `ce_shared.pricing` imports.

---

## Requirement Cross-Reference

Phase 01 is mapped to 11 requirements: SHPK-01, SHPK-02, SHPK-03, PRIC-01 through PRIC-08.

| Req ID | Description | Status | Evidence |
|--------|-------------|--------|----------|
| SHPK-01 | ce-shared package exists at repo root with src layout, zero external deps | PASS | `ce-shared/pyproject.toml` has no dependencies, uses `src/ce_shared/` layout |
| SHPK-02 | ce-shared installable via `file:` reference from sub-projects | PASS | Agent Builder: `ce-shared @ file:../ce-shared` in pyproject.toml. Orchestration: `ce-shared @ file:../ce-shared` in requirements.txt |
| SHPK-03 | ce-shared uses editable installs so changes propagate without reinstall | **FAIL** | Installed as regular package, not editable. `direct_url.json` lacks `"editable": true` |
| PRIC-01 | Single pricing.py with all Anthropic pricing (Opus $5/$25, Sonnet $3/$15, Haiku $0.80/$4 per MTok) | **PARTIAL** | Pricing exists and is correct for Opus/Sonnet. REQUIREMENTS.md says Haiku $0.80/$4 but actual implementation uses $1/$5. Plan 01-01 documents this as an intentional correction (REQUIREMENTS.md was wrong per Anthropic docs). Pricing is verified correct. |
| PRIC-02 | Pricing dict keyed by exact model ID with substring fallback matching | PASS | `MODEL_PRICING` dict with exact keys + `_SUBSTRING_FALLBACKS` list with ordered substring matching |
| PRIC-03 | Each pricing entry includes "last verified" date stamp | **PARTIAL** | `PRICING_VERIFIED_DATE = "2026-03-09"` exists as a module-level constant, but it is a single global date, not per-entry. REQUIREMENTS.md says "each pricing entry" -- the implementation uses one date for the entire module. Reasonable simplification for a single-provider pricing table. |
| PRIC-04 | Cache read/write and batch discount multipliers consolidated in shared module | PASS | `CACHE_READ_MULTIPLIER = 0.10`, `CACHE_WRITE_MULTIPLIER = 1.25`, `BATCH_DISCOUNT = 0.50` all in `pricing.py` |
| PRIC-05 | Centralized model alias map resolves shorthand ("opus") to canonical model ID | **PARTIAL** | Substring fallback resolves "opus" to correct **pricing** `(5.00, 25.00)` but does NOT resolve shorthand to canonical model ID string (e.g., "opus" -> "claude-opus-4-6"). No explicit alias map exists. `ModelTier` enum provides canonical IDs but no reverse lookup function. |
| PRIC-06 | Pricing verification script compares local prices against billing data | **FAIL** | No verification script exists anywhere in ce-shared. No `scripts/` directory. Plan 01-02 and 01-03 both claim this requirement but neither created a script. |
| PRIC-07 | Agent Builder cost tracker imports from ce-shared | PASS | `cost_tracker.py` line 29-36: imports `BATCH_DISCOUNT`, `CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER`, `MODEL_PRICING`, `ModelTier`, `get_pricing` from ce-shared |
| PRIC-08 | Orchestration cost tracker imports from ce-shared | PASS | `cost_tracker.py` line 21: imports `cost_for_model`, `get_pricing` from ce-shared |

---

## Summary

| Category | Count |
|----------|-------|
| Requirements PASS | 6 of 11 |
| Requirements PARTIAL | 3 of 11 |
| Requirements FAIL | 2 of 11 |
| Success Criteria PASS | 3 of 4 |
| Success Criteria FAIL | 1 of 4 |

### Issues Requiring Action

1. **SHPK-03 / Success Criterion 3 (FAIL):** ce-shared is not installed as editable. Run `pip install -e ../ce-shared` to fix. This is the most impactful gap -- it defeats the purpose of a shared package for development.

2. **PRIC-06 (FAIL):** No pricing verification script exists. Neither Plan 02 nor Plan 03 actually created one despite both claiming this requirement. Requires a new script in `ce-shared/scripts/` that compares `MODEL_PRICING` against Anthropic Admin API billing data.

3. **PRIC-05 (PARTIAL):** Substring fallback resolves to pricing tuples, not to canonical model ID strings. If the intent is to resolve "opus" -> "claude-opus-4-6" (as stated in REQUIREMENTS.md), a `resolve_model_id()` function is needed alongside `get_pricing()`.

### Minor Notes

- PRIC-01 Haiku pricing: REQUIREMENTS.md says $0.80/$4 but implementation uses $1/$5. Plan 01-01 documents this as a correction based on verified Anthropic docs. The implementation is correct; REQUIREMENTS.md should be updated.
- PRIC-03 per-entry date: Single module-level date is a reasonable simplification but deviates from "each pricing entry" language. Acceptable for v1.
- Both venvs appear to share the same global Python environment (`/Users/scottewalt/.pyenv/versions/3.13.11/`), which may mask venv isolation issues.

---

### Requirement Coverage from Plan Summaries

| Plan | Claims | Actually Delivered |
|------|--------|--------------------|
| 01-01 | SHPK-01, SHPK-02, SHPK-03, PRIC-01, PRIC-02, PRIC-03, PRIC-04, PRIC-05 | SHPK-01, SHPK-02 delivered. SHPK-03 not editable. PRIC-01 through PRIC-04 delivered. PRIC-05 partial. |
| 01-02 | PRIC-06, PRIC-07 | PRIC-07 delivered. PRIC-06 not delivered (no verification script created). |
| 01-03 | PRIC-06, PRIC-08 | PRIC-08 delivered. PRIC-06 not delivered (duplicate claim, still missing). |

---
*Verified: 2026-03-09*
