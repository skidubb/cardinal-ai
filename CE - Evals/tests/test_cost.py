"""Tests for cost estimation."""

from ce_evals.core.cost import estimate_cost, PRICING


def test_known_model_cost():
    cost = estimate_cost(1_000_000, 1_000_000, "claude-opus-4-6")
    assert cost == 5.0 + 25.0  # $30 (ce-shared canonical pricing)


def test_openai_model_cost():
    cost = estimate_cost(1000, 1000, "gpt-5.2")
    expected = (1000 * 2.50 + 1000 * 10.0) / 1_000_000
    assert abs(cost - expected) < 1e-9


def test_unknown_model_returns_default():
    cost = estimate_cost(1000, 1000, "totally-unknown-model")
    # ce-shared defaults to Opus pricing for unknown models
    assert cost > 0


def test_zero_tokens():
    cost = estimate_cost(0, 0, "claude-opus-4-6")
    assert cost == 0.0
