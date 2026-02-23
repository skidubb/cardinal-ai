"""Tests for cost estimation."""

from ce_evals.core.cost import estimate_cost, PRICING


def test_known_model_cost():
    cost = estimate_cost(1_000_000, 1_000_000, "claude-opus-4-6")
    assert cost == 15.0 + 75.0  # $90


def test_openai_model_cost():
    cost = estimate_cost(1000, 1000, "gpt-5.2")
    expected = (1000 * 2.50 + 1000 * 10.0) / 1_000_000
    assert abs(cost - expected) < 1e-9


def test_unknown_model_returns_zero():
    cost = estimate_cost(1000, 1000, "totally-unknown-model")
    assert cost == 0.0


def test_prefix_match():
    # "claude-opus-4" should prefix-match "claude-opus-4-6" (after rsplit)
    cost = estimate_cost(1_000_000, 0, "claude-opus-4-6-extended")
    # Should match claude-opus-4-6 via prefix
    assert cost > 0


def test_zero_tokens():
    cost = estimate_cost(0, 0, "claude-opus-4-6")
    assert cost == 0.0
