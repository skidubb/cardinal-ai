# CLAUDE.md — ce-shared

**Single source of truth** for model pricing and env-var names across all Python projects. When a model ID, price, or env key changes, it changes here — never inline in a consuming project.

## Layout

```
src/ce_shared/
├── pricing.py    # MODEL_PRICING, cost_for_model() — canonical model IDs + $/MTok
├── env.py        # KEY_REGISTRY, find_and_load_dotenv() — canonical env-var names
└── env_check.py  # Startup env validation
```

## Rules

- New model or price change → edit `MODEL_PRICING` only; consumers (`csuite`, protocols, evals) import it.
- New env var → register it in `KEY_REGISTRY` so `find_and_load_dotenv()` and env checks know about it.
- Consumed via `ce-shared @ file:../ce-shared` (Orchestration) and editable installs (`pip install -e ../ce-shared`) elsewhere — this package must stay dependency-light.

See [README.md](README.md) for API details. Conventions per root [CLAUDE.md](../CLAUDE.md).
