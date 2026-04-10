# ce-shared

Shared utilities for the CE-AGENTS monorepo. Provides unified model pricing data and environment variable management used by CE - Agent Builder, CE - Multi-Agent Orchestration, and CE - Evals.

> **Audience:** Internal developers only.

## Installation

From the monorepo root, install as an editable package:

```bash
pip install -e ce-shared/
```

This is typically done inside each project's virtual environment so that all projects reference the same source.

## Modules

### `ce_shared.pricing` — Model Pricing & Cost Calculation

Single source of truth for Anthropic model pricing across the monorepo. Includes cost calculation, token estimation, and pricing lookup with substring fallback.

```python
from ce_shared.pricing import get_pricing, cost_for_model, estimate_tokens_from_cost

# Look up pricing for a model (returns input_per_mtok, output_per_mtok)
input_rate, output_rate = get_pricing("claude-opus-4-6")
# (5.0, 25.0)

# Calculate cost for a known token count
cost = cost_for_model(
    model="claude-opus-4-6",
    input_tokens=10_000,
    output_tokens=2_000,
)
# 0.1  (USD)

# Back-calculate estimated tokens from a known cost
estimate = estimate_tokens_from_cost("claude-opus-4-6", cost_usd=0.15)
# {"input_tokens": 12500, "output_tokens": 2500, "token_source": "estimated_from_cost"}
```

**Key exports:**
- `MODEL_PRICING` — Dict of all model pricing entries `{model_id: (input_per_mtok, output_per_mtok)}`
- `ModelTier` — StrEnum of canonical Anthropic model tiers (OPUS, SONNET, HAIKU)
- `get_pricing(model)` — Lookup with exact match, substring fallback, and conservative default
- `cost_for_model(model, input_tokens, output_tokens, ...)` — Calculate USD cost
- `estimate_tokens_from_cost(model, cost_usd, input_output_ratio=5.0)` — Inverse cost calculation
- `PRICING_VERIFIED_DATE` — Date pricing was last verified against provider docs
- `BATCH_DISCOUNT`, `CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER` — Pricing modifiers

### `ce_shared.env` — Environment Variable Loading & Validation

Finds and loads the monorepo root `.env` file from any working directory. Provides a key registry for validation and diagnostics.

```python
from ce_shared.env import find_and_load_dotenv, validate_env, KEY_REGISTRY

# Load .env from monorepo root (walks up from CWD)
env_path = find_and_load_dotenv()
# Loaded .env from /path/to/CE-AGENTS/.env

# Load with project-scoped validation
env_path = find_and_load_dotenv(project="agent-builder")

# Validate current environment (returns list of warnings)
warnings = validate_env(project="orchestration")

# Inspect the key registry
for key, meta in KEY_REGISTRY.items():
    print(f"{key}: required={meta.required}, project={meta.project}")
```

**Key exports:**
- `find_and_load_dotenv(project=None)` — Find root `.env`, load it, validate, return path
- `validate_env(project=None)` — Check required/optional keys, return warnings
- `KEY_REGISTRY` — Dict of `KeyMeta` objects describing every known env var
- `KeyMeta` — Dataclass with `required`, `project`, `description`, etc.

### `ce_shared.env_check` — Diagnostic CLI

Run from any directory to check environment status across all projects:

```bash
python -m ce_shared.env_check
```

## Development

### Running Tests

```bash
pytest ce-shared/tests/ -v
```

### Dependencies

`ce-shared` has one external dependency: `python-dotenv` (for `.env` loading in the env module). The pricing module uses stdlib only.

All projects in the monorepo install `ce-shared` as an editable dependency, so changes are reflected immediately without reinstallation.

---
*Internal developer reference — not for client distribution*
