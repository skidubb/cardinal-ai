"""Tests for ce_shared.pricing module."""

from enum import StrEnum

from ce_shared import (
    BATCH_DISCOUNT,
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    MODEL_PRICING,
    PRICING_VERIFIED_DATE,
    ModelTier,
    cost_for_model,
    get_pricing,
)


# ---------------------------------------------------------------------------
# 1. Import succeeds for all public symbols
# ---------------------------------------------------------------------------


def test_all_public_symbols_importable():
    """All public symbols are importable from ce_shared."""
    assert MODEL_PRICING is not None
    assert ModelTier is not None
    assert cost_for_model is not None
    assert get_pricing is not None
    assert PRICING_VERIFIED_DATE is not None
    assert CACHE_READ_MULTIPLIER is not None
    assert CACHE_WRITE_MULTIPLIER is not None
    assert BATCH_DISCOUNT is not None


# ---------------------------------------------------------------------------
# 2-4. Exact model cost calculations
# ---------------------------------------------------------------------------


def test_opus_cost():
    """Opus 4.6: 1M input + 1M output = $5 + $25 = $30."""
    result = cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000)
    assert result == 30.00


def test_sonnet_cost():
    """Sonnet 4.6: 1M input + 1M output = $3 + $15 = $18."""
    result = cost_for_model("claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert result == 18.00


def test_haiku_cost():
    """Haiku 4.5: 1M input + 1M output = $1 + $5 = $6."""
    result = cost_for_model("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
    assert result == 6.00


# ---------------------------------------------------------------------------
# 5. Substring fallback
# ---------------------------------------------------------------------------


def test_substring_fallback_resolves_to_opus():
    """A model string containing 'opus' resolves to Opus pricing."""
    result = cost_for_model("anthropic/claude-opus-4-6", 1000, 1000)
    expected = cost_for_model("claude-opus-4-6", 1000, 1000)
    assert result == expected


# ---------------------------------------------------------------------------
# 6. Unknown model defaults to Opus
# ---------------------------------------------------------------------------


def test_unknown_model_defaults_to_opus():
    """Unknown model strings default to current Opus-tier pricing."""
    result = cost_for_model("some-unknown-model", 1_000_000, 1_000_000)
    opus_result = cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000)
    assert result == opus_result


# ---------------------------------------------------------------------------
# 7. Cache read multiplier
# ---------------------------------------------------------------------------


def test_cache_read_multiplier():
    """Cache read tokens are charged at 10% of normal input rate."""
    input_rate, _ = get_pricing("claude-opus-4-6")
    per_token = input_rate / 1_000_000

    # 1000 cache_read_tokens at 0.10x input rate
    result = cost_for_model("claude-opus-4-6", 0, 0, cache_read_tokens=1000)
    expected = 1000 * per_token * CACHE_READ_MULTIPLIER
    assert abs(result - expected) < 1e-12


# ---------------------------------------------------------------------------
# 8. Cache write multiplier
# ---------------------------------------------------------------------------


def test_cache_write_multiplier():
    """Cache write tokens are charged at 125% of normal input rate."""
    input_rate, _ = get_pricing("claude-opus-4-6")
    per_token = input_rate / 1_000_000

    # 1000 cache_write_tokens at 1.25x input rate
    result = cost_for_model("claude-opus-4-6", 0, 0, cache_write_tokens=1000)
    expected = 1000 * per_token * CACHE_WRITE_MULTIPLIER
    assert abs(result - expected) < 1e-12


# ---------------------------------------------------------------------------
# 9. Batch discount
# ---------------------------------------------------------------------------


def test_batch_discount():
    """Batch mode applies 50% discount to total cost."""
    normal = cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000)
    batched = cost_for_model("claude-opus-4-6", 1_000_000, 1_000_000, batch=True)
    assert batched == normal * (1 - BATCH_DISCOUNT)


# ---------------------------------------------------------------------------
# 10. Non-Anthropic model lookups
# ---------------------------------------------------------------------------


def test_gpt4o_lookup():
    """GPT-4o has explicit pricing entry."""
    input_rate, output_rate = get_pricing("gpt-4o")
    assert input_rate == 2.50
    assert output_rate == 10.00


def test_gemini_flash_lookup():
    """Gemini 2.0 Flash has explicit pricing entry."""
    input_rate, output_rate = get_pricing("gemini-2.0-flash")
    assert input_rate == 0.10
    assert output_rate == 0.40


# ---------------------------------------------------------------------------
# 11. ModelTier is a StrEnum with 3 members
# ---------------------------------------------------------------------------


def test_model_tier_is_strenum():
    """ModelTier is a stdlib StrEnum with exactly 3 members."""
    assert issubclass(ModelTier, StrEnum)
    assert len(ModelTier) == 3
    assert ModelTier.OPUS.value == "claude-opus-4-6"
    assert ModelTier.SONNET.value == "claude-sonnet-4-6"
    assert ModelTier.HAIKU.value == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# 12. PRICING_VERIFIED_DATE is a non-empty string
# ---------------------------------------------------------------------------


def test_pricing_verified_date():
    """PRICING_VERIFIED_DATE is set and non-empty."""
    assert isinstance(PRICING_VERIFIED_DATE, str)
    assert len(PRICING_VERIFIED_DATE) > 0


# ---------------------------------------------------------------------------
# Multiplier constant values
# ---------------------------------------------------------------------------


def test_multiplier_values():
    """Multiplier constants have the documented values."""
    assert CACHE_READ_MULTIPLIER == 0.10
    assert CACHE_WRITE_MULTIPLIER == 1.25
    assert BATCH_DISCOUNT == 0.50
