"""Drift audit for the fat/thin agent identity bridge."""

from __future__ import annotations

import pytest

from protocols import agent_identity


def test_thin_prompts_present_for_all_csuite() -> None:
    """Every C-Suite key must have a thin prompt in BUILTIN_AGENTS."""
    for key in agent_identity.CSUITE_KEYS:
        thin = agent_identity.get_thin_prompt(key)
        assert thin, f"thin prompt missing for {key}"


def test_thin_prompts_mention_expected_role_name() -> None:
    """Thin prompts must name their role — the display tier is the source of
    truth for the role label used in synthesis prompts.
    """
    for key in agent_identity.CSUITE_KEYS:
        expected = agent_identity._EXPECTED_ROLE_NAMES[key]
        thin = agent_identity.get_thin_prompt(key) or ""
        assert expected.lower() in thin.lower(), (
            f"thin prompt for {key} does not name its role '{expected}'"
        )


def test_identity_check_returns_shape() -> None:
    check = agent_identity.identity_check("ceo")
    assert check.key == "ceo"
    assert check.thin_available is True
    # fat side may or may not be importable in this env; either is fine here.
    assert isinstance(check.verdict, str) and check.verdict


def test_identity_check_gracefully_handles_unknown_key() -> None:
    check = agent_identity.identity_check("no-such-agent-xyz")
    assert not check.thin_available
    assert not check.fat_available
    assert "thin_missing" in check.verdict


def test_get_fat_prompt_returns_none_for_unknown_key() -> None:
    assert agent_identity.get_fat_prompt("no-such-agent-xyz") is None


def test_drift_report_covers_every_csuite_key() -> None:
    report = agent_identity.drift_report()
    for key in agent_identity.CSUITE_KEYS:
        assert key in report, f"drift report missing {key}"


@pytest.mark.parametrize("key", agent_identity.CSUITE_KEYS)
def test_no_role_drift_when_both_sides_available(key: str) -> None:
    """When both fat and thin exist, their role names must agree.

    Skips (does not fail) when Agent Builder isn't importable — that's the
    research-mode / headless-CI case, not a drift issue.
    """
    check = agent_identity.identity_check(key)
    if not check.fat_available:
        pytest.skip(f"Agent Builder not importable in this env — cannot check {key}")
    assert check.role_name_match, (
        f"{key} role name drift: thin={check.thin_opener!r} fat={check.fat_opener!r}"
    )
