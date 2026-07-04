"""Tests for the Adaptive Router — resolver rails + orchestrator gate."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from protocols.adaptive_router import (
    AdaptiveRouterOrchestrator,
    Resolver,
    ResolveError,
)
from protocols.adaptive_router.resolver import DEFAULT_ALLOWLIST


# ── Resolver ────────────────────────────────────────────────────────────────


def test_resolver_maps_protocol_id_to_key():
    resolver = Resolver(max_cost_tier="high")
    plan = resolver.resolve(
        recommended_protocol_id="P4",
        alternatives=[],
        requested_agents=["ceo", "cfo"],
    )
    assert plan.protocol_key == "p04_multi_round_debate"
    assert plan.protocol_id == "P4"
    assert plan.agent_keys == ["ceo", "cfo"]


def test_resolver_backfills_missing_agents():
    resolver = Resolver(max_cost_tier="high")
    plan = resolver.resolve(
        recommended_protocol_id="P4",
        alternatives=[],
        requested_agents=["ceo"],  # below min_agents=2
    )
    assert len(plan.agent_keys) >= 2
    assert any("backfilled" in a for a in plan.adjustments)


def test_resolver_uses_default_agents_when_none_provided():
    resolver = Resolver(max_cost_tier="high")
    plan = resolver.resolve(
        recommended_protocol_id="P4",
        alternatives=[],
        requested_agents=None,
    )
    assert plan.agent_keys == ["ceo", "cfo", "cto"]
    assert any("defaults" in a for a in plan.adjustments)


def test_resolver_falls_back_to_alternative_when_primary_not_allowlisted():
    # Allowlist only P4; recommend P99 (unknown), fall back to P4.
    resolver = Resolver(
        allowlist=frozenset({"p04_multi_round_debate"}),
        max_cost_tier="high",
    )
    plan = resolver.resolve(
        recommended_protocol_id="P99",
        alternatives=[("P4", "Multi-Round Debate")],
        requested_agents=["ceo", "cfo"],
    )
    assert plan.protocol_id == "P4"
    assert any("P99 unknown" in a for a in plan.adjustments)


def test_resolver_blocks_protocols_above_cost_ceiling():
    # Find a high-tier protocol in the manifest to exercise the ceiling.
    from protocols.adaptive_router.resolver import _load_manifest

    manifest = _load_manifest()
    high_tier = [
        cap.get("protocol_id")
        for cap in manifest.values()
        if cap.get("cost_tier") == "high" and cap.get("protocol_id")
    ]
    if not high_tier:
        pytest.skip("no high-tier protocols in manifest")
    pid = high_tier[0]

    resolver = Resolver(max_cost_tier="low")
    with pytest.raises(ResolveError):
        resolver.resolve(
            recommended_protocol_id=pid,
            alternatives=[],
            requested_agents=["ceo", "cfo"],
        )


def test_resolver_raises_when_nothing_routable():
    resolver = Resolver(
        allowlist=frozenset({"p04_multi_round_debate"}),
        max_cost_tier="medium",
    )
    with pytest.raises(ResolveError):
        resolver.resolve(
            recommended_protocol_id="P999",
            alternatives=[("P888", "Nonexistent")],
            requested_agents=["ceo", "cfo"],
        )


def test_default_allowlist_keys_exist_in_manifest():
    """Every allowlisted protocol must be loadable."""
    from protocols.adaptive_router.resolver import _load_manifest

    manifest = _load_manifest()
    for key in DEFAULT_ALLOWLIST:
        assert key in manifest, f"{key} in allowlist but has no capability.yaml"


# ── Orchestrator confidence gate ────────────────────────────────────────────


@dataclass
class _FakeAlt:
    protocol: str
    name: str
    reason: str


@dataclass
class _FakeRouterResult:
    question: str
    features: dict
    problem_type: str
    problem_type_confidence: int
    recommended_protocol: str
    recommended_name: str
    alternatives: list
    reasoning: str
    cost_tier: str
    timings: dict


def _fake_classifier(confidence: int, pid: str = "P4"):
    classifier = AsyncMock()
    classifier.run = AsyncMock(
        return_value=_FakeRouterResult(
            question="q",
            features={"complexity": 3},
            problem_type="Prioritization",
            problem_type_confidence=confidence,
            recommended_protocol=pid,
            recommended_name="Multi-Round Debate",
            alternatives=[_FakeAlt("P3", "Parallel Synthesis", "fallback")],
            reasoning="test",
            cost_tier="medium",
            timings={"phase1_features": 0.1},
        )
    )
    return classifier


@pytest.mark.asyncio
async def test_gate_high_confidence_auto_executable():
    orch = AdaptiveRouterOrchestrator(
        classifier=_fake_classifier(90),
        resolver=Resolver(max_cost_tier="high"),
    )
    decision = await orch.decide("q", requested_agents=["ceo", "cfo"])
    assert decision.tier == "high"
    assert decision.auto_executable is True
    assert decision.plan is not None


@pytest.mark.asyncio
async def test_gate_mid_confidence_not_auto_executable():
    orch = AdaptiveRouterOrchestrator(
        classifier=_fake_classifier(65),
        resolver=Resolver(max_cost_tier="high"),
    )
    decision = await orch.decide("q", requested_agents=["ceo", "cfo"])
    assert decision.tier == "mid"
    assert decision.auto_executable is False


@pytest.mark.asyncio
async def test_gate_low_confidence_refused():
    orch = AdaptiveRouterOrchestrator(
        classifier=_fake_classifier(30),
        resolver=Resolver(max_cost_tier="high"),
    )
    decision = await orch.decide("q", requested_agents=["ceo", "cfo"])
    assert decision.tier == "low"
    assert decision.auto_executable is False


@pytest.mark.asyncio
async def test_decision_to_dict_is_json_safe():
    import json

    orch = AdaptiveRouterOrchestrator(
        classifier=_fake_classifier(90),
        resolver=Resolver(max_cost_tier="high"),
    )
    decision = await orch.decide("q", requested_agents=["ceo", "cfo"])
    payload = decision.to_dict()
    json.dumps(payload)  # must not raise
    assert payload["tier"] == "high"
    assert payload["plan"]["protocol_key"] == "p04_multi_round_debate"
