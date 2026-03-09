"""Tests for ProtocolCostTracker budget ceiling feature."""

from __future__ import annotations

import logging
import os

import pytest

from protocols.cost_tracker import ProtocolCostTracker


@pytest.fixture(autouse=True)
def _clear_ceiling_env(monkeypatch: pytest.MonkeyPatch):
    """Ensure PROTOCOL_COST_CEILING is unset unless a test sets it explicitly."""
    monkeypatch.delenv("PROTOCOL_COST_CEILING", raising=False)


# ---- helpers ----------------------------------------------------------------

def _track_cost(tracker: ProtocolCostTracker, model: str = "claude-haiku-4-5-20251001",
                input_tokens: int = 5000, output_tokens: int = 1000) -> None:
    """Fire one track() call with token counts that produce a known cost."""
    tracker.track(model=model, input_tokens=input_tokens, output_tokens=output_tokens)


# ---- tests ------------------------------------------------------------------

def test_ceiling_warning_fires(caplog: pytest.LogCaptureFixture):
    """Warning is logged when total cost exceeds the ceiling."""
    tracker = ProtocolCostTracker(cost_ceiling_usd=0.001)
    with caplog.at_level(logging.WARNING, logger="protocols.cost_tracker"):
        _track_cost(tracker, input_tokens=10_000, output_tokens=5_000)
    assert any("exceeds ceiling" in rec.message for rec in caplog.records), (
        f"Expected ceiling warning, got: {[r.message for r in caplog.records]}"
    )


def test_no_warning_under_ceiling(caplog: pytest.LogCaptureFixture):
    """No warning when cost stays under the ceiling."""
    tracker = ProtocolCostTracker(cost_ceiling_usd=100.0)
    with caplog.at_level(logging.WARNING, logger="protocols.cost_tracker"):
        _track_cost(tracker, input_tokens=100, output_tokens=10)
    warnings = [r for r in caplog.records if "exceeds ceiling" in r.message]
    assert len(warnings) == 0, f"Unexpected warning: {warnings}"


def test_ceiling_from_env(monkeypatch: pytest.MonkeyPatch):
    """Ceiling is loaded from PROTOCOL_COST_CEILING env var when not passed explicitly."""
    monkeypatch.setenv("PROTOCOL_COST_CEILING", "1.00")
    tracker = ProtocolCostTracker()
    assert tracker.cost_ceiling_usd == 1.0


def test_ceiling_warns_once(caplog: pytest.LogCaptureFixture):
    """Ceiling warning fires only once even when cost exceeds on multiple track() calls."""
    tracker = ProtocolCostTracker(cost_ceiling_usd=0.001)
    with caplog.at_level(logging.WARNING, logger="protocols.cost_tracker"):
        _track_cost(tracker, input_tokens=10_000, output_tokens=5_000)
        _track_cost(tracker, input_tokens=10_000, output_tokens=5_000)
    warnings = [r for r in caplog.records if "exceeds ceiling" in r.message]
    assert len(warnings) == 1, f"Expected exactly 1 warning, got {len(warnings)}: {warnings}"
