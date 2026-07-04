"""Tests for protocols/model_catalog.py — routing, litellm id mapping, pricing agreement."""

from __future__ import annotations

import pytest

from protocols.model_catalog import (
    CATALOG,
    ModelRoute,
    litellm_id_for,
    resolve_route,
    supports_tools,
)


# ── resolve_route ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "model_id",
    [m.id for m in CATALOG.values() if m.route == ModelRoute.ANTHROPIC],
)
def test_resolve_route_catalog_anthropic(model_id):
    assert resolve_route(model_id) == ModelRoute.ANTHROPIC


@pytest.mark.parametrize(
    "model_id",
    [m.id for m in CATALOG.values() if m.route == ModelRoute.GATEWAY],
)
def test_resolve_route_catalog_gateway(model_id):
    assert resolve_route(model_id) == ModelRoute.GATEWAY


def test_resolve_route_unknown_claude_like_goes_anthropic():
    assert resolve_route("claude-nonexistent-9-9") == ModelRoute.ANTHROPIC


def test_resolve_route_unknown_non_claude_goes_gateway():
    assert resolve_route("foo-bar") == ModelRoute.GATEWAY


# ── litellm_id_for ───────────────────────────────────────────────────────────


def test_litellm_id_for_catalog_entries_return_declared_id():
    for model in CATALOG.values():
        assert litellm_id_for(model.id) == model.litellm_id


def test_litellm_id_for_passthrough_for_slash_strings():
    assert litellm_id_for("openai/gpt-5.2") == "openai/gpt-5.2"
    assert litellm_id_for("vercel_ai_gateway/some/provider-model") == (
        "vercel_ai_gateway/some/provider-model"
    )


def test_litellm_id_for_prefixes_bare_unknown_models():
    assert litellm_id_for("some-new-model") == "vercel_ai_gateway/some-new-model"


# ── supports_tools ───────────────────────────────────────────────────────────


def test_supports_tools_matches_catalog_flag():
    for model in CATALOG.values():
        assert supports_tools(model.id) == model.supports_anthropic_tool_loop


def test_supports_tools_unknown_model_falls_back_to_route():
    assert supports_tools("claude-nonexistent-9-9") is True
    assert supports_tools("foo-bar") is False


# ── catalog <-> ce_shared pricing agreement ──────────────────────────────────


def test_catalog_anthropic_pricing_agrees_with_ce_shared():
    """For every catalog entry present in ce_shared.MODEL_PRICING, the display
    prices here must match the billing-authoritative prices there.

    A teammate is adding the new Anthropic models (claude-fable-5, etc.) to
    ce_shared.MODEL_PRICING in parallel — this test iterates the intersection
    so it tightens automatically once that lands, rather than hard-failing on
    entries that aren't there yet.
    """
    from ce_shared.pricing import MODEL_PRICING

    anthropic_entries = [m for m in CATALOG.values() if m.route == ModelRoute.ANTHROPIC]
    checked = 0
    for model in anthropic_entries:
        if model.id not in MODEL_PRICING:
            continue
        checked += 1
        assert MODEL_PRICING[model.id] == (model.input_price, model.output_price), (
            f"{model.id}: catalog price {(model.input_price, model.output_price)} != "
            f"ce_shared price {MODEL_PRICING[model.id]}"
        )
    if checked == 0:
        pytest.skip(
            "No catalog Anthropic models found in ce_shared.MODEL_PRICING yet — "
            "pricing addition is landing in a parallel change."
        )
