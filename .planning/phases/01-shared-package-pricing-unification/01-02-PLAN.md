---
phase: 1
plan: 2
title: "Migrate Agent Builder cost tracker to ce-shared"
wave: 2
depends_on: [1]
requirements: [PRIC-06, PRIC-07]
files_modified:
  - CE - Agent Builder/src/csuite/tools/cost_tracker.py
  - CE - Agent Builder/pyproject.toml
autonomous: true
---

# Plan 2: Migrate Agent Builder cost tracker to ce-shared

## Objective
Remove all local pricing definitions from Agent Builder's `cost_tracker.py` and replace them with imports from `ce_shared.pricing`. This eliminates one of the two duplicate pricing sources and ensures Agent Builder uses the verified shared pricing.

## must_haves
- `ModelTier`, `MODEL_PRICING`, `CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER`, `BATCH_DISCOUNT` are no longer defined in Agent Builder's `cost_tracker.py` — they are imported from `ce_shared.pricing`
- `_get_pricing()` method on `UsageRecord` calls `ce_shared.pricing.get_pricing()` instead of doing its own lookup
- `_calculate_costs()` method uses imported multiplier constants from ce_shared
- `calculate_model_tier_cost()` standalone function uses imported `MODEL_PRICING` and multipliers from ce_shared (or delegates to `cost_for_model()`)
- `ce-shared` is listed as a dependency in Agent Builder's `pyproject.toml`
- All existing Agent Builder tests still pass (no behavioral changes, only source-of-truth changes)
- `calculate_cost_per_audit()` and `calculate_monthly_burn_rate()` are NOT modified (they use hardcoded per-task costs, not per-MTok pricing)

<tasks>
<task id="1">
Add `ce-shared` as a dependency in `CE - Agent Builder/pyproject.toml`. Use path reference: `"ce-shared @ file:../ce-shared"` in the `dependencies` list. Run `pip install -e "CE - Agent Builder/[dev]"` to verify the dependency resolves.
</task>
<task id="2">
In `CE - Agent Builder/src/csuite/tools/cost_tracker.py`:
- Delete the `ModelTier(StrEnum)` class definition (lines ~33-38)
- Delete the `MODEL_PRICING` dict (lines ~41-48)
- Delete `BATCH_DISCOUNT`, `CACHE_WRITE_MULTIPLIER`, `CACHE_READ_MULTIPLIER` constants (lines ~50-56)
- Add imports at top: `from ce_shared.pricing import ModelTier, MODEL_PRICING, CACHE_READ_MULTIPLIER, CACHE_WRITE_MULTIPLIER, BATCH_DISCOUNT, get_pricing, cost_for_model`
</task>
<task id="3">
Rewrite `UsageRecord._get_pricing()` method (lines ~157-171) to delegate to `get_pricing(self.model)` from ce_shared. It should return the same `tuple[float, float]` format. Keep the method signature identical so callers are unaffected.
</task>
<task id="4">
Rewrite `UsageRecord._calculate_costs()` method (lines ~127-155) to use the imported `CACHE_READ_MULTIPLIER` and `BATCH_DISCOUNT` constants from ce_shared (they are now imports rather than local constants, so the code logic stays the same — just verify the references resolve).
</task>
<task id="5">
Update `calculate_model_tier_cost()` function (lines ~1018-1075) to use the imported `MODEL_PRICING`, `CACHE_READ_MULTIPLIER`, and `BATCH_DISCOUNT` from ce_shared. Consider simplifying it to delegate to `cost_for_model()` if the signatures align, but preserve the function's return type and behavior.
</task>
<task id="6">
Verify no local pricing constants remain: grep `cost_tracker.py` for any remaining `MODEL_PRICING =`, `_get_pricing` dict literals, `BATCH_DISCOUNT =`, `CACHE_READ_MULTIPLIER =`, `CACHE_WRITE_MULTIPLIER =`, or `class ModelTier` definitions. Only imports of these names should exist.
</task>
<task id="7">
Run existing Agent Builder tests: `cd "CE - Agent Builder" && pytest tests/ -m "not integration" -x`. Fix any import errors or test failures caused by the migration. Do NOT modify test assertions about pricing values unless they test against the old wrong values.
</task>
</tasks>

## Verification
1. `grep -n "MODEL_PRICING\s*=" "CE - Agent Builder/src/csuite/tools/cost_tracker.py"` returns zero matches (no local definition)
2. `grep -n "class ModelTier" "CE - Agent Builder/src/csuite/tools/cost_tracker.py"` returns zero matches
3. `python -c "from csuite.tools.cost_tracker import ModelTier, MODEL_PRICING; print(type(ModelTier.OPUS))"` succeeds (re-exported from ce_shared)
4. `pytest "CE - Agent Builder/tests/" -m "not integration" -x` passes
5. Agent Builder's `pyproject.toml` contains `ce-shared` in dependencies
