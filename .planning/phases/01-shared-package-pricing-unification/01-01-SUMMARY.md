---
phase: 01-shared-package-pricing-unification
plan: 01
subsystem: pricing
tags: [python, hatchling, pricing, strenum, anthropic, openai, gemini]

requires:
  - phase: none
    provides: first plan in phase
provides:
  - ce-shared package with unified MODEL_PRICING dict
  - cost_for_model() function with cache/batch support
  - ModelTier StrEnum for canonical model tiers
  - Verified pricing for 20 model variants (Anthropic, OpenAI, Google)
affects: [01-02, 01-03, phase-2, phase-3]

tech-stack:
  added: [ce-shared (hatchling package)]
  patterns: [shared package at repo root, tuple-based pricing dict, substring fallback lookup]

key-files:
  created:
    - ce-shared/pyproject.toml
    - ce-shared/src/ce_shared/__init__.py
    - ce-shared/src/ce_shared/pricing.py
    - ce-shared/src/ce_shared/py.typed
    - ce-shared/tests/test_pricing.py
  modified:
    - .planning/ROADMAP.md

key-decisions:
  - "Opus 4.6 priced at $5/$25 (not $15/$75) — Orchestration tracker had stale Opus 4.0/4.1 pricing"
  - "Haiku 4.5 priced at $1/$5 (not $0.80/$4) — Orchestration tracker was wrong"
  - "Substring fallback order includes version-specific opus variants before generic 'opus' to handle Opus 4.1 ($15/$75) vs Opus 4.6 ($5/$25) correctly"
  - "Unknown models default to current Opus-tier ($5/$25) as conservative fallback"

patterns-established:
  - "Shared package pattern: ce-shared/ at repo root, pip install -e for editable development"
  - "Pricing as tuple[float, float] instead of dict for cleaner destructuring"

requirements-completed: [SHPK-01, SHPK-02, SHPK-03, PRIC-01, PRIC-02, PRIC-03, PRIC-04, PRIC-05]

duration: 3 min
completed: 2026-03-09
---

# Phase 1 Plan 1: Create ce-shared Package with Verified Pricing Summary

**Unified pricing module with 20 verified model rates, ModelTier StrEnum, cache/batch multipliers, and 14 passing tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T19:59:32Z
- **Completed:** 2026-03-09T20:02:50Z
- **Tasks:** 7
- **Files modified:** 6

## Accomplishments
- Created `ce-shared` Python package at repo root with hatchling build system and zero external dependencies
- Verified all Anthropic pricing against official docs — discovered Orchestration tracker had wrong Opus ($15/$75 instead of correct $5/$25) and wrong Haiku ($0.80/$4 instead of correct $1/$5)
- Built `cost_for_model()` with exact match, substring fallback (version-aware), cache read/write, and batch discount support
- 14 comprehensive tests all passing, covering every plan requirement

## Task Commits

Each task was committed atomically:

1. **Task 1: Create directory structure** - `0af583a` (feat)
2. **Task 2: Create pyproject.toml** - `43203dc` (chore)
3. **Task 3: Verify pricing and update ROADMAP** - `0db69cc` (docs)
4. **Task 4: Create pricing.py module** - `3e35256` (feat)
5. **Task 5: Re-export symbols from __init__.py** - `175cc18` (feat)
6. **Task 6: Create test_pricing.py** - `5aff6a7` (test)
7. **Task 7: Install, test, fix pyproject.toml** - `6a8fc9e` (fix)

## Files Created/Modified
- `ce-shared/pyproject.toml` - Package config (hatchling, v0.1.0, no deps)
- `ce-shared/src/ce_shared/__init__.py` - Re-exports all public pricing symbols
- `ce-shared/src/ce_shared/pricing.py` - MODEL_PRICING, ModelTier, cost_for_model, get_pricing, multiplier constants
- `ce-shared/src/ce_shared/py.typed` - PEP 561 type marker
- `ce-shared/tests/test_pricing.py` - 14 pytest tests covering all requirements
- `.planning/ROADMAP.md` - Corrected Haiku pricing in success criteria

## Decisions Made
- Opus 4.6 is $5/$25 per MTok (the Orchestration tracker had $15/$75 which is the older Opus 4.0/4.1 price)
- Haiku 4.5 is $1/$5 per MTok (Orchestration had $0.80/$4 which was incorrect)
- Substring fallback includes version-specific opus variants (opus-4-6, opus-4-5, opus-4-1) before generic "opus" to correctly differentiate pricing across Opus generations
- Unknown models default to current Opus ($5/$25) rather than legacy Opus ($15/$75)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed readme reference from pyproject.toml**
- **Found during:** Task 7 (install and test)
- **Issue:** `pyproject.toml` referenced `readme = "README.md"` but no README exists; hatchling build failed
- **Fix:** Removed the `readme` field from pyproject.toml
- **Files modified:** ce-shared/pyproject.toml
- **Verification:** `pip install -e ce-shared/` succeeds; all 14 tests pass
- **Committed in:** `6a8fc9e`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal — missing README reference was a packaging oversight, no scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ce-shared package ready for Plans 2 and 3 (migrate Agent Builder and Orchestration cost trackers)
- Both projects can `pip install -e ../ce-shared/` and import `from ce_shared.pricing import MODEL_PRICING, cost_for_model`
- Verified pricing eliminates the 3x Opus discrepancy between trackers

---
*Phase: 01-shared-package-pricing-unification*
*Completed: 2026-03-09*
