# Phase 1: Shared Package & Pricing Unification - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the `ce-shared` package with verified Anthropic pricing (and all non-Anthropic models used in the monorepo) and migrate both cost trackers to use it, eliminating the 3x pricing discrepancy between Agent Builder and Orchestration.

</domain>

<decisions>
## Implementation Decisions

### Correct Pricing Values
- Verify ALL model pricing against current Anthropic public pricing before locking in — do not trust either tracker's existing values
- Include all non-Anthropic models used in the monorepo (OpenAI, Gemini via LiteLLM) — single source of truth for all model costs
- Include `PRICING_VERIFIED_DATE` module-level constant (e.g., `PRICING_VERIFIED_DATE = "2026-03-09"`) so stale pricing is visible
- Update ROADMAP.md success criteria to match verified prices (current criteria may have wrong values)
- Price updates: edit the Python dict and reinstall — no dynamic config files

### ce-shared Package Scope
- Phase 1 scope: pricing module only (`ce_shared.pricing`)
- Location: `ce-shared/` at repo root, parallel to `ce-db/`
- Source layout: `ce-shared/src/ce_shared/pricing.py`
- Build system: hatchling (matches Agent Builder)
- Exports: `MODEL_PRICING` dict + `cost_for_model()` helper function + `ModelTier` StrEnum + multiplier constants

### Migration Depth
- Replace local pricing dicts AND lookup functions in both trackers — import from `ce_shared.pricing` instead
- Move `ModelTier` StrEnum from Agent Builder's cost_tracker.py into `ce_shared.pricing`
- Agent Builder: delete `MODEL_PRICING`, `_get_pricing()`, `ModelTier` from cost_tracker.py; import from ce_shared
- Orchestration: delete `_PRICING` dict and `_price_for_model()` from cost_tracker.py; import from ce_shared
- Leave all analytics, trend analysis, markdown reporting, and ProtocolCostTracker logic untouched
- Orchestration imports only — no re-exports of ce_shared pricing

### Cache & Batch Pricing
- All three multipliers live in ce-shared: `CACHE_READ_MULTIPLIER` (0.10x), `CACHE_WRITE_MULTIPLIER` (1.25x), `BATCH_DISCOUNT` (0.50x)
- `cost_for_model()` helper handles cache/batch via optional params: `cost_for_model(model, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0, batch=False)`
- Default fallback for unrecognized model strings: Opus-tier pricing (most conservative — overestimates rather than underestimates)

### Claude's Discretion
- Internal module structure within ce-shared (single file vs subpackage)
- Exact function signatures and type annotations
- How to structure the model-substring fallback matching
- Whether to add a py.typed marker for mypy

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CE - Agent Builder/src/csuite/tools/cost_tracker.py`: 860+ line tracker with `ModelTier` StrEnum, `MODEL_PRICING` dict, `UsageRecord` dataclass, analytics pipeline. Pricing section (lines 33-56) will be extracted.
- `CE - Multi-Agent Orchestration/protocols/cost_tracker.py`: 80-line lightweight tracker with `_PRICING` dict, `_price_for_model()`, `ProtocolCostTracker` dataclass. Pricing section (lines 22-50) will be replaced.

### Established Patterns
- `ce-db/` is the existing shared package pattern: `src/ce_db/` layout, setuptools build, editable install
- Both trackers use model-substring fallback (check exact ID first, then match "opus"/"sonnet"/"haiku" substring)
- Agent Builder uses StrEnum for model tiers; Orchestration uses plain strings
- Pydantic v2 in Agent Builder, dataclasses in Orchestration — ce-shared should stay dependency-light

### Integration Points
- Agent Builder's `pyproject.toml` needs `ce-shared` as editable dependency
- Orchestration's `requirements.txt` needs `-e ../ce-shared` or equivalent path dependency
- Both projects' venvs need `pip install -e ../ce-shared`
- Success criterion: `from ce_shared.pricing import MODEL_PRICING` works in both venvs

</code_context>

<specifics>
## Specific Ideas

- All model costs in one place — Anthropic AND non-Anthropic (OpenAI, Gemini) used anywhere in the monorepo
- The helper function should be the "one function to calculate cost" — callers shouldn't need to know about multipliers or fallback logic

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-shared-package-pricing-unification*
*Context gathered: 2026-03-09*
