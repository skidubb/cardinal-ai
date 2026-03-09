---
phase: 01-shared-package-pricing-unification
plan: 02
subsystem: pricing
tags: [python, cost-tracker, ce-shared, pricing-migration]

requires:
  - phase: 01-shared-package-pricing-unification
    provides: ce-shared package with MODEL_PRICING, ModelTier, get_pricing, multiplier constants
provides:
  - Agent Builder cost tracker using ce-shared as single source of truth for pricing
  - Eliminated duplicate pricing definitions from Agent Builder
affects: [01-03, phase-3]

tech-stack:
  added: []
  patterns: [ce-shared tuple-to-dict adapter in _get_pricing()]

key-files:
  created: []
  modified:
    - CE - Agent Builder/pyproject.toml
    - CE - Agent Builder/src/csuite/tools/cost_tracker.py

key-decisions:
  - "Adapted _get_pricing() to convert ce-shared tuple (input, output) to dict format for backward compatibility with _calculate_costs()"
  - "Used get_pricing() from ce-shared for both _get_pricing() and calculate_model_tier_cost() — delegates all lookup logic to shared module"

patterns-established:
  - "Migration pattern: import from ce-shared, adapt tuple to dict where needed, preserve method signatures"

requirements-completed: [PRIC-06, PRIC-07]

duration: 3 min
completed: 2026-03-09
---

# Phase 1 Plan 2: Migrate Agent Builder Cost Tracker to ce-shared Summary

**Agent Builder cost_tracker.py now imports all pricing from ce-shared, eliminating local ModelTier/MODEL_PRICING/multiplier definitions — 148 tests passing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T20:05:27Z
- **Completed:** 2026-03-09T20:08:34Z
- **Tasks:** 7
- **Files modified:** 2

## Accomplishments
- Removed all local pricing definitions (ModelTier, MODEL_PRICING, BATCH_DISCOUNT, CACHE_READ_MULTIPLIER, CACHE_WRITE_MULTIPLIER) from Agent Builder's cost_tracker.py
- Rewrote `_get_pricing()` and `calculate_model_tier_cost()` to delegate to `ce_shared.pricing.get_pricing()`
- All 148 existing Agent Builder tests pass with zero behavioral changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ce-shared dependency** - `674b235` (chore)
2. **Task 2: Delete local constants, add imports** - `1681ba3` (feat)
3. **Task 3: Rewrite _get_pricing()** - `631f5f6` (feat)
4. **Task 4: Verify _calculate_costs()** - no commit (constants already resolved via imports, no code change needed)
5. **Task 5: Update calculate_model_tier_cost()** - `7052997` (feat)
6. **Task 6: Verify no local constants remain** - no commit (verification only)
7. **Task 7: Run tests and fix** - `33520a5` (fix — restored StrEnum import)

## Files Created/Modified
- `CE - Agent Builder/pyproject.toml` - Added ce-shared dependency + hatch direct-reference config
- `CE - Agent Builder/src/csuite/tools/cost_tracker.py` - Replaced local pricing with ce-shared imports

## Decisions Made
- Adapted `_get_pricing()` to return `dict[str, float]` from ce-shared's `tuple[float, float]` — preserves the dict-based interface that `_calculate_costs()` depends on without requiring a broader refactor
- Used `get_pricing()` instead of raw `MODEL_PRICING` dict access for both lookup sites — this delegates exact match, substring fallback, and default logic entirely to ce-shared

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored StrEnum import removed with ModelTier deletion**
- **Found during:** Task 7 (test run)
- **Issue:** Removing the local `ModelTier(StrEnum)` class also removed the `from enum import StrEnum` import, but `TaskType(StrEnum)` in the same module still needs it
- **Fix:** Added `from enum import StrEnum` back to imports
- **Files modified:** CE - Agent Builder/src/csuite/tools/cost_tracker.py
- **Verification:** All 148 tests pass
- **Committed in:** `33520a5`

**2. [Rule 3 - Blocking] Added hatch direct-reference config for file-based dependency**
- **Found during:** Task 1 (pip install)
- **Issue:** Hatchling rejects `file:../ce-shared` dependencies by default
- **Fix:** Added `[tool.hatch.metadata] allow-direct-references = true` to pyproject.toml
- **Files modified:** CE - Agent Builder/pyproject.toml
- **Verification:** `pip install -e ".[dev]"` succeeds
- **Committed in:** `674b235`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both were necessary for the migration to work. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Agent Builder fully migrated to ce-shared pricing
- Ready for Plan 3: Migrate Orchestration cost tracker
- After Plan 3, all pricing across the monorepo will use a single source of truth

---
*Phase: 01-shared-package-pricing-unification*
*Completed: 2026-03-09*
