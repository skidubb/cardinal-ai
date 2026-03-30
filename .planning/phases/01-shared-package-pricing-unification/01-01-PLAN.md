---
phase: 1
plan: 1
title: "Create ce-shared package with verified pricing"
wave: 1
depends_on: []
requirements: [SHPK-01, SHPK-02, SHPK-03, PRIC-01, PRIC-02, PRIC-03, PRIC-04, PRIC-05]
files_modified:
  - ce-shared/pyproject.toml
  - ce-shared/src/ce_shared/__init__.py
  - ce-shared/src/ce_shared/pricing.py
  - ce-shared/src/ce_shared/py.typed
  - ce-shared/tests/test_pricing.py
autonomous: true
---

# Plan 1: Create ce-shared package with verified pricing

## Objective
Create the `ce-shared` Python package at the repo root with a `pricing` module containing verified Anthropic and non-Anthropic model pricing, the `ModelTier` StrEnum, cache/batch multiplier constants, and the `cost_for_model()` helper function. This package becomes the single source of truth for all model pricing across the monorepo.

## must_haves
- `ce-shared/` package exists at repo root with hatchling build system and zero external dependencies
- `from ce_shared.pricing import MODEL_PRICING, cost_for_model, ModelTier` succeeds after `pip install -e ce-shared/`
- `MODEL_PRICING` contains verified pricing for all Anthropic models (Opus, Sonnet, Haiku with all known model ID variants) plus non-Anthropic models (GPT-4o, GPT-5.2, o3-mini, Gemini variants) found in the codebase
- `PRICING_VERIFIED_DATE` constant is set to the date pricing was verified against provider pages
- `cost_for_model()` handles exact match, substring fallback, cache_read_tokens, cache_write_tokens, and batch discount — defaults to Opus-tier for unknown models
- `CACHE_READ_MULTIPLIER` (0.10), `CACHE_WRITE_MULTIPLIER` (1.25), and `BATCH_DISCOUNT` (0.50) are exported constants
- `ModelTier` is a stdlib `StrEnum` (not Pydantic) with OPUS, SONNET, HAIKU values
- Unit tests pass covering: exact lookup, substring fallback, unknown model default, cache pricing, batch discount, all multiplier values

<tasks>
<task id="1">
Create directory structure: `ce-shared/src/ce_shared/` with `__init__.py` and `py.typed` marker. Create `ce-shared/tests/` directory.
</task>
<task id="2">
Create `ce-shared/pyproject.toml` using hatchling build system, version 0.1.0, requires-python >=3.11, no external dependencies. Include `[tool.hatch.build.targets.wheel]` with `packages = ["src/ce_shared"]`.
</task>
<task id="3">
Verify ALL model pricing against current Anthropic public pricing page (https://www.anthropic.com/pricing) and OpenAI/Google pricing pages. Document verified values. Update ROADMAP.md success criteria (line 15) with the correct verified prices — the current values mix wrong Opus pricing from Agent Builder with Orchestration's Haiku pricing.
</task>
<task id="4">
Create `ce-shared/src/ce_shared/pricing.py` with:
- `PRICING_VERIFIED_DATE` string constant
- `ModelTier(StrEnum)` with OPUS, SONNET, HAIKU (values are the canonical model ID strings: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`)
- `CACHE_READ_MULTIPLIER = 0.10`, `CACHE_WRITE_MULTIPLIER = 1.25`, `BATCH_DISCOUNT = 0.50`
- `MODEL_PRICING: dict[str, tuple[float, float]]` — superset of all model IDs from both trackers plus non-Anthropic models from CE-Evals. Keys are model ID strings, values are `(input_per_mtok, output_per_mtok)`.
- `get_pricing(model: str) -> tuple[float, float]` — exact match, then substring fallback (opus/sonnet/haiku/gpt/gemini), then Opus default.
- `cost_for_model(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0, cache_write_tokens: int = 0, batch: bool = False) -> float` — calculates total USD cost using `get_pricing()` and multiplier constants.
</task>
<task id="5">
Create `ce-shared/src/ce_shared/__init__.py` that re-exports all public symbols from `pricing.py`: `MODEL_PRICING`, `ModelTier`, `cost_for_model`, `get_pricing`, `PRICING_VERIFIED_DATE`, `CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER`, `BATCH_DISCOUNT`.
</task>
<task id="6">
Create `ce-shared/tests/test_pricing.py` with pytest tests:
1. Import succeeds for all public symbols
2. `cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000)` returns expected value
3. `cost_for_model("claude-sonnet-4-6", 1_000_000, 1_000_000)` returns expected value
4. `cost_for_model("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)` returns expected value
5. Substring fallback: `cost_for_model("anthropic/claude-opus-4-6", 1000, 1000)` resolves to Opus
6. Unknown model defaults to Opus: `cost_for_model("some-unknown-model", 1_000_000, 1_000_000)` == Opus cost
7. Cache read: verify 0.10x multiplier applied to cache_read_tokens input cost
8. Cache write: verify 1.25x multiplier applied to cache_write_tokens input cost
9. Batch discount: verify 0.50x applied to total
10. Non-Anthropic model lookup: `cost_for_model("gpt-4o", ...)` and `cost_for_model("gemini-2.0-flash", ...)` return expected values
11. `ModelTier` is a `StrEnum` with 3 members
12. `PRICING_VERIFIED_DATE` is a non-empty string
</task>
<task id="7">
Run `pip install -e ce-shared/` in a temporary venv and run `pytest ce-shared/tests/` to verify everything works. Fix any issues.
</task>
</tasks>

## Verification
1. `pip install -e ce-shared/` succeeds with no dependency errors
2. `python -c "from ce_shared.pricing import MODEL_PRICING, cost_for_model, ModelTier; print(len(MODEL_PRICING))"` prints a count > 10 (all models)
3. `pytest ce-shared/tests/test_pricing.py -v` — all tests pass
4. ROADMAP.md success criteria pricing values match verified prices
5. `MODEL_PRICING` is a superset of all model IDs found in Agent Builder and Orchestration trackers
