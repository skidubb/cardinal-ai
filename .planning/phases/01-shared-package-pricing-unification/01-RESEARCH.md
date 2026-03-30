# Phase 1 Research: Shared Package & Pricing Unification

**Researched:** 2026-03-09
**Status:** Complete

---

## 1. Pricing Discrepancy Analysis

### Agent Builder (`CE - Agent Builder/src/csuite/tools/cost_tracker.py`, lines 41-48)

```
Opus:   $5.00 input  / $25.00 output  (per MTok)
Sonnet: $3.00 input  / $15.00 output
Haiku:  $1.00 input  /  $5.00 output
```

Header comment says "February 2026 Anthropic Pricing."

### Orchestration (`CE - Multi-Agent Orchestration/protocols/cost_tracker.py`, lines 26-38)

```
Opus:   $15.00 input / $75.00 output  (per MTok)
Sonnet:  $3.00 input / $15.00 output
Haiku:   $0.80 input /  $4.00 output
```

Header comment says "Anthropic public pricing, March 2026."

### CE - Evals (`CE - Evals/src/ce_evals/core/cost.py`, lines 6-18)

```
Opus:   $15.00 input / $75.00 output
Sonnet:  $3.00 input / $15.00 output
Haiku:   $0.80 input /  $4.00 output
```

Comment says "Feb 2026 pricing." Also includes OpenAI and Google models.

### Discrepancy Summary

| Model | Agent Builder | Orchestration | CE-Evals | Factor |
|-------|--------------|---------------|----------|--------|
| Opus input | $5.00 | $15.00 | $15.00 | **3x** |
| Opus output | $25.00 | $75.00 | $75.00 | **3x** |
| Sonnet input | $3.00 | $3.00 | $3.00 | match |
| Sonnet output | $15.00 | $15.00 | $15.00 | match |
| Haiku input | $1.00 | $0.80 | $0.80 | **1.25x** |
| Haiku output | $5.00 | $4.00 | $4.00 | **1.25x** |

**Verdict:** Agent Builder has wrong Opus and Haiku pricing. Orchestration and CE-Evals agree. The correct values must be verified against Anthropic's public pricing page at implementation time, as the CONTEXT.md decision explicitly states: "Verify ALL model pricing against current Anthropic public pricing before locking in -- do not trust either tracker's existing values."

### ROADMAP.md Success Criteria Issue

The ROADMAP.md (line 15) states success criteria as: "Opus $5/$25, Sonnet $3/$15, Haiku $0.80/$4.00" -- this mixes Agent Builder's wrong Opus pricing ($5/$25) with Orchestration's Haiku pricing ($0.80/$4.00). Per the CONTEXT.md decision, this must be corrected after verification.

---

## 2. ce-db Package Template

**Location:** `/Users/scottewalt/Documents/CE - AGENTS/ce-db/`

### Structure
```
ce-db/
  pyproject.toml          # setuptools, version 0.1.0, requires-python >=3.11
  src/
    ce_db/
      __init__.py         # Re-exports all public symbols
      engine.py
      session.py
      models/
        __init__.py
        core.py
        runs.py
        evals.py
  alembic/                # DB migrations (not relevant for ce-shared)
  alembic.ini
```

### Key Observations for ce-shared
- **Build system:** setuptools (not hatchling). The CONTEXT.md decision says ce-shared should use hatchling to match Agent Builder.
- **Package layout:** `src/ce_db/` -- standard src layout. ce-shared should mirror: `src/ce_shared/`.
- **Dependencies:** ce-db has heavy deps (sqlalchemy, asyncpg, alembic). ce-shared must be dependency-free (zero external deps) since it's just pricing constants and a helper function.
- **How it's consumed:** Orchestration's `requirements.txt` references it as `ce-db @ file:../ce-db`. Agent Builder doesn't use ce-db.
- **Egg-info present:** `ce-db/src/ce_db.egg-info/` exists, confirming editable install works.

### Recommended ce-shared Structure
```
ce-shared/
  pyproject.toml          # hatchling, no dependencies
  src/
    ce_shared/
      __init__.py         # Re-export pricing symbols
      pricing.py          # MODEL_PRICING, cost_for_model(), ModelTier, multiplier constants
      py.typed            # Optional: mypy marker
```

---

## 3. Cost Tracker File Analysis

### Agent Builder (`CE - Agent Builder/src/csuite/tools/cost_tracker.py`)

**Total lines:** 1114
**What to extract (lines 33-56):**
- `ModelTier(StrEnum)` -- 3 values: OPUS, SONNET, HAIKU with exact model IDs
- `MODEL_PRICING` dict -- 6 entries (3 exact + 3 substring fallbacks)
- `BATCH_DISCOUNT = 0.50`
- `CACHE_WRITE_MULTIPLIER = 1.25`
- `CACHE_READ_MULTIPLIER = 0.10`

**What to replace:**
- `_get_pricing()` method on `UsageRecord` (lines 157-171) -- currently does exact match then substring fallback. Should call `ce_shared.pricing.cost_for_model()` or equivalent lookup.
- `_calculate_costs()` method (lines 127-155) -- uses `MODEL_PRICING`, `CACHE_READ_MULTIPLIER`, `BATCH_DISCOUNT` directly. These references change to imports from ce_shared.

**What stays untouched:**
- `TaskType(StrEnum)` and `TASK_TOKEN_BENCHMARKS` (lines 63-89) -- task classification, not pricing
- `UsageRecord(BaseModel)` (lines 96-171) -- data model stays, just rewire `_get_pricing()` and `_calculate_costs()`
- `AggregatedMetrics(BaseModel)` (lines 174-209)
- `CostAlert(BaseModel)` (lines 211-218)
- `CostTracker` class (lines 225-882) -- all logging, aggregation, trend analysis, anomaly detection, reporting
- `calculate_cost_per_audit()` (lines 889-953) -- standalone formula using hardcoded per-task costs (not per-MTok pricing)
- `calculate_monthly_burn_rate()` (lines 956-1015) -- standalone formula
- `calculate_model_tier_cost()` (lines 1018-1075) -- uses `MODEL_PRICING` directly, needs to import from ce_shared

**Dependency note:** Agent Builder's cost_tracker.py uses `pydantic.BaseModel` and `StrEnum`. After migration, it will import `ModelTier` from `ce_shared.pricing` (which has no pydantic dependency), so ce_shared's `ModelTier` must be a plain `StrEnum` from the stdlib.

### Orchestration (`CE - Multi-Agent Orchestration/protocols/cost_tracker.py`)

**Total lines:** 224
**What to extract (lines 26-52):**
- `_PRICING` dict -- 9 entries (6 exact model IDs + 3 substring fallbacks)
- `_CACHE_READ_MULTIPLIER = 0.10`
- `_price_for_model()` function
- `_compute_cost()` function

**What to replace:**
- `_PRICING` dict and `_CACHE_READ_MULTIPLIER` -- delete, import from ce_shared
- `_price_for_model()` -- delete, use ce_shared's lookup
- `_compute_cost()` -- replace body to call `ce_shared.pricing.cost_for_model()`. **Critical:** This function is imported directly by `protocols/llm.py` (line 171) for Langfuse cost recording. The function must remain importable at `protocols.cost_tracker._compute_cost` or `llm.py` must be updated too.

**What stays untouched:**
- `_ModelStats` and `_AgentStats` dataclasses (lines 76-96)
- `ProtocolCostTracker` class (lines 103-224) -- all accumulation and summary logic

**External consumers of `_compute_cost`:**
- `protocols/llm.py` line 171: `from protocols.cost_tracker import _compute_cost`
- This import must keep working. Options: (a) keep `_compute_cost` as a thin wrapper that calls ce_shared, or (b) update llm.py to import from ce_shared directly.

### CE-Evals (`CE - Evals/src/ce_evals/core/cost.py`)

**Total lines:** 37. Contains its own `PRICING` dict and `estimate_cost()` function.
**In scope?** The CONTEXT.md decisions scope Phase 1 to Agent Builder and Orchestration only. However, CE-Evals has a third copy of pricing data (38 lines) that will become stale. This is a natural candidate for Phase 1 scope creep -- recommend noting it but deferring unless trivial to include.

---

## 4. Dependency Files

### Agent Builder (`CE - Agent Builder/pyproject.toml`)

- Build system: hatchling
- No reference to ce-db or any local packages
- Need to add: `ce-shared` as a dependency (editable for dev)
- Hatchling editable install: `pip install -e ../ce-shared` in the Agent Builder venv, then add `"ce-shared"` to the `dependencies` list (or use a path dependency)

### Orchestration (`CE - Multi-Agent Orchestration/requirements.txt`)

```
anthropic>=0.83.0
litellm>=1.40.0
langfuse>=2.0.0
python-dotenv>=1.0.0
pyyaml>=6.0
ce-db @ file:../ce-db
PyMuPDF>=1.25.0
pinecone>=5.0.0
```

- Already has `ce-db @ file:../ce-db` pattern -- add `ce-shared @ file:../ce-shared` the same way
- Uses `pip install -r requirements.txt` (not pyproject.toml)

### CE-Evals (`CE - Evals/pyproject.toml`)

- Build system: setuptools
- Has `ce-db` as optional: `db = ["ce-db @ file:../ce-db"]`
- If CE-Evals is included, add `"ce-shared @ file:../ce-shared"` to dependencies

---

## 5. Model String Matching / Fallback Logic

### Agent Builder Pattern (lines 157-171)
1. Try exact match against `ModelTier` enum values
2. Substring match: check if `model.lower()` contains "opus", "sonnet", or "haiku"
3. Default: Opus pricing (conservative)

### Orchestration Pattern (lines 43-52)
1. Try exact key lookup in `_PRICING` dict
2. Substring match: check if `model.lower()` contains "opus", "sonnet", or "haiku"
3. Default: Opus pricing (conservative)

### Key Differences
- Agent Builder checks enum values first, Orchestration checks dict keys
- Both do the same substring fallback in the same order
- Both default to Opus (conservative)
- **Unified approach:** The ce_shared `cost_for_model()` helper should: (1) exact dict lookup, (2) substring match for tier keywords, (3) default to Opus. The `ModelTier` StrEnum gives callers type-safe access but isn't required for the lookup.

### Orchestration Has More Exact Model IDs
Orchestration's `_PRICING` dict includes model IDs not in Agent Builder:
- `claude-opus-4-5` (older Opus)
- `claude-sonnet-4-6` (newer Sonnet)
- `claude-haiku-4-5` (without date suffix)

The ce-shared dict should be the superset of all model IDs found across both trackers.

---

## 6. Non-Anthropic Model Pricing

### Models Found in Codebase

| Model | Where Used | Current Pricing |
|-------|-----------|----------------|
| `openai/gpt-4o` | Agent Builder config.py (vc-app-investor agent) | Not tracked |
| `gemini/gemini-2.0-flash` | Agent Builder config.py (vc-infra-investor agent) | Not tracked |
| `gemini/gemini-3-pro-preview` | Orchestration agents.py (vc-infra-investor agent) | Not tracked |
| `gpt-5.2` | CE-Evals cost.py | $2.50/$10.00 |
| `gpt-4o` | CE-Evals cost.py | $2.50/$10.00 |
| `o3-mini` | CE-Evals cost.py | $1.10/$4.40 |
| `gemini-3.1-pro-preview` | CE-Evals cost.py | $1.25/$5.00 |
| `gemini-2.5-pro` | CE-Evals cost.py | $1.25/$5.00 |

### How Non-Anthropic Calls Are Tracked Today

In Orchestration, `protocols/llm.py` routes non-Anthropic agents through LiteLLM (`litellm.acompletion`). The `_record_usage()` function extracts `input_tokens`/`output_tokens` from the LiteLLM response and passes them to `ProtocolCostTracker.track()`. The tracker then calls `_price_for_model()` which falls through to the Opus fallback for any non-Anthropic model string. This means **non-Anthropic models are currently costed at Opus rates** -- wildly incorrect.

In Agent Builder, the `openai/gpt-4o` and `gemini/gemini-2.0-flash` models are in config but go through SDK agents (`agent.chat()`), which bypasses the cost tracker entirely (SDK backend reports USD total but 0 tokens).

### Recommendation

Per CONTEXT.md: "Include all non-Anthropic models used in the monorepo -- single source of truth for all model costs." The ce-shared pricing dict should include entries for:
- `openai/gpt-4o` (and bare `gpt-4o`)
- `gemini/gemini-2.0-flash` (and bare form)
- `gemini/gemini-3-pro-preview` (and bare form)
- Optionally: `gpt-5.2`, `o3-mini`, `gemini-2.5-pro`, `gemini-3.1-pro-preview` from CE-Evals

The substring fallback should also handle non-Anthropic patterns (e.g., "gpt" -> GPT-4o tier, "gemini" -> Gemini tier). Verify all pricing against provider pricing pages at implementation time.

---

## 7. Validation Architecture

### How to Verify the Migration Works

**Unit tests for ce-shared itself:**
1. `from ce_shared.pricing import MODEL_PRICING, cost_for_model, ModelTier` -- import succeeds
2. `cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000)` returns expected USD
3. `cost_for_model("claude-opus-4-6", 1_000_000, 0, cache_read_tokens=500_000)` applies 0.10x multiplier
4. `cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000, batch=True)` applies 0.50x discount
5. `cost_for_model("some-unknown-model", 1000, 1000)` defaults to Opus tier
6. Substring matching: `cost_for_model("anthropic/claude-opus-4-6", 1000, 1000)` resolves correctly

**Integration tests for Agent Builder:**
1. Instantiate `UsageRecord(agent="CFO", model="claude-opus-4-6", input_tokens=1_000_000, output_tokens=1_000_000)` and verify `total_cost` matches ce-shared's calculation
2. Verify no `MODEL_PRICING` or `_get_pricing` exists in Agent Builder's cost_tracker.py (grep test)
3. Run `csuite ceo "test"` and verify the cost log file uses correct pricing

**Integration tests for Orchestration:**
1. Instantiate `ProtocolCostTracker`, call `tracker.track("claude-opus-4-6", 1_000_000, 1_000_000)`, verify `tracker.total_cost` matches ce-shared
2. Verify `_compute_cost` still importable from `protocols.cost_tracker` (backward compat for llm.py)
3. Verify no `_PRICING` dict in Orchestration's cost_tracker.py (grep test)
4. Run a protocol and verify cost summary uses correct pricing

**Editable install verification:**
1. `pip install -e ../ce-shared` in both venvs
2. Change a price value in `ce-shared/src/ce_shared/pricing.py`
3. Without reinstalling, run `python -c "from ce_shared.pricing import MODEL_PRICING; print(MODEL_PRICING)"` in both venvs and verify the change is reflected

---

## 8. Risk Factors and Edge Cases

### `_compute_cost` Import Chain
`protocols/llm.py` imports `_compute_cost` from `protocols.cost_tracker` (line 171). After migration, this function's body changes but the import path must remain stable. Either keep it as a thin wrapper or update llm.py.

### Cache Write Multiplier
Agent Builder defines `CACHE_WRITE_MULTIPLIER = 1.25` but never uses it in `_calculate_costs()`. Orchestration doesn't define it at all. The CONTEXT.md says to include it in ce-shared. It should be exported but documented as currently unused.

### Batch Discount in Orchestration
Agent Builder supports `is_batch` flag and applies `BATCH_DISCOUNT`. Orchestration's `_compute_cost` does not support batch. The ce-shared `cost_for_model()` should support it (per CONTEXT.md), and Orchestration can simply not pass it.

### `calculate_cost_per_audit()` and `calculate_monthly_burn_rate()`
These functions in Agent Builder (lines 889-1015) use hardcoded per-task cost estimates (e.g., `opus_cost = 0.225`), not the `MODEL_PRICING` dict. They are NOT affected by the pricing migration and should be left alone.

### `calculate_model_tier_cost()` (Agent Builder line 1018)
This standalone function directly references `MODEL_PRICING`, `CACHE_READ_MULTIPLIER`, and `BATCH_DISCOUNT`. After migration, these imports change to ce_shared. This function largely duplicates what `cost_for_model()` in ce_shared will do -- consider whether to deprecate it in favor of the shared helper.

### CE-Evals Third Copy
CE-Evals has a third pricing dict at `CE - Evals/src/ce_evals/core/cost.py`. It's out of explicit Phase 1 scope but only 37 lines. Including it would eliminate all three copies. The test file (`tests/test_cost.py`) imports `PRICING` directly -- would need updating.

---

## 9. Complete File Inventory

| File | Action | Lines Affected |
|------|--------|---------------|
| `ce-shared/pyproject.toml` | **Create** | New file (~20 lines) |
| `ce-shared/src/ce_shared/__init__.py` | **Create** | New file (~10 lines) |
| `ce-shared/src/ce_shared/pricing.py` | **Create** | New file (~80-100 lines) |
| `CE - Agent Builder/src/csuite/tools/cost_tracker.py` | **Edit** | Delete lines 33-56 (ModelTier, MODEL_PRICING, multipliers), rewrite _get_pricing/_calculate_costs to use ce_shared |
| `CE - Agent Builder/pyproject.toml` | **Edit** | Add ce-shared dependency |
| `CE - Multi-Agent Orchestration/protocols/cost_tracker.py` | **Edit** | Delete lines 26-52 (_PRICING, _CACHE_READ_MULTIPLIER, _price_for_model), rewrite _compute_cost |
| `CE - Multi-Agent Orchestration/requirements.txt` | **Edit** | Add ce-shared line |
| `CE - Multi-Agent Orchestration/protocols/llm.py` | **Possibly edit** | Line 171 imports _compute_cost -- verify still works |
| `.planning/ROADMAP.md` | **Edit** | Fix success criteria pricing values after verification |

---

*Phase: 01-shared-package-pricing-unification*
*Research completed: 2026-03-09*
