---
phase: 03-token-estimation-documentation
plan: 01
subsystem: pricing
tags: [token-estimation, cost-tracking, inverse-calculation]

requires:
  - phase: 01-shared-package-pricing-unification
    provides: ce-shared pricing module with cost_for_model() and get_pricing()
provides:
  - estimate_tokens_from_cost() function for back-calculating tokens from USD cost
affects: [ce-multi-agent-orchestration, ce-agent-builder, cost-tracking]

tech-stack:
  added: []
  patterns: [inverse-cost-calculation, configurable-ratio-estimation]

key-files:
  created: []
  modified:
    - ce-shared/src/ce_shared/pricing.py
    - ce-shared/src/ce_shared/__init__.py
    - ce-shared/tests/test_pricing.py

key-decisions:
  - "Formula: output_tokens = cost * 1M / (ratio * input_rate + output_rate), input_tokens = ratio * output_tokens"
  - "max(1, round(...)) guarantees at least 1 token per field for non-zero cost"

patterns-established:
  - "Inverse pricing calculation: estimate_tokens_from_cost is the inverse of cost_for_model"

requirements-completed: [TOKN-01, TOKN-04]

duration: 1 min
completed: 2026-03-09
---

# Phase 3 Plan 1: Token Estimation Function Summary

**`estimate_tokens_from_cost()` added to ce-shared pricing module — inverse of `cost_for_model()` with configurable input:output ratio and round-trip accuracy within 5%**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-09T21:15:25Z
- **Completed:** 2026-03-09T21:16:36Z
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments
- Added `estimate_tokens_from_cost(model, cost_usd, input_output_ratio=5.0)` to `ce_shared.pricing`
- Re-exported from `ce_shared.__init__` for top-level access
- 6 comprehensive unit tests covering basic, zero-cost, unknown model, round-trip, minimum-1, and custom ratio cases
- Full test suite (37 tests) passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add estimate_tokens_from_cost()** - `7857a41` (feat)
2. **Task 2: Re-export from __init__** - `3d75be4` (feat)
3. **Task 3: Add 6 unit tests** - `1c90065` (test)
4. **Task 4: Full regression check** - no commit needed (verification only)

## Files Created/Modified
- `ce-shared/src/ce_shared/pricing.py` - Added estimate_tokens_from_cost() function
- `ce-shared/src/ce_shared/__init__.py` - Added re-export of estimate_tokens_from_cost
- `ce-shared/tests/test_pricing.py` - Added 6 new test functions for token estimation

## Decisions Made
- Formula uses algebraic inversion of cost_for_model: `output_tokens = cost * 1M / (ratio * input_rate + output_rate)`
- `max(1, round(...))` ensures non-zero cost always yields at least 1 token per field
- Zero/negative cost short-circuits to all zeros (no division needed)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Token estimation function ready for integration into protocol cost tracking
- Ready for Plan 02 (next plan in phase 3)

---
*Phase: 03-token-estimation-documentation*
*Completed: 2026-03-09*
