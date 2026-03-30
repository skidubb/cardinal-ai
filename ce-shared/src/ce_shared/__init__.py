"""ce-shared: Shared utilities for the CE-AGENTS monorepo."""

from ce_shared.env import (
    KEY_REGISTRY,
    KeyMeta,
    find_and_load_dotenv,
    validate_env,
)
from ce_shared.pricing import (
    BATCH_DISCOUNT,
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    MODEL_PRICING,
    PRICING_VERIFIED_DATE,
    ModelTier,
    cost_for_model,
    estimate_tokens_from_cost,
    get_pricing,
)

__all__ = [
    # env
    "KEY_REGISTRY",
    "KeyMeta",
    "find_and_load_dotenv",
    "validate_env",
    # pricing
    "BATCH_DISCOUNT",
    "CACHE_READ_MULTIPLIER",
    "CACHE_WRITE_MULTIPLIER",
    "MODEL_PRICING",
    "PRICING_VERIFIED_DATE",
    "ModelTier",
    "cost_for_model",
    "estimate_tokens_from_cost",
    "get_pricing",
]
