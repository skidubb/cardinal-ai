"""Live integration tests — require a real ANTHROPIC_API_KEY.

Skipped in CI (pytest -m "not integration").
"""

from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def require_api_key():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-test"):
        pytest.skip("Real ANTHROPIC_API_KEY required for integration tests")


@pytest.mark.timeout(60)
@pytest.mark.asyncio
async def test_p03_parallel_synthesis_live():
    """Run P03 Parallel Synthesis end-to-end with a trivial question."""
    from protocols.p03_parallel_synthesis.orchestrator import SynthesisOrchestrator

    agents = [
        {"name": "analyst-a", "system_prompt": "You are a concise analyst. Keep answers under 50 words."},
        {"name": "analyst-b", "system_prompt": "You are a concise analyst. Keep answers under 50 words."},
    ]

    orchestrator = SynthesisOrchestrator(
        agents=agents,
        thinking_budget=1_024,
    )

    result = await orchestrator.run("What is 2+2?")

    assert result is not None
    assert result.synthesis, "Synthesis should contain text"
    assert len(result.perspectives) == 2
    for p in result.perspectives:
        assert p.response, f"Agent {p.name} returned empty response"
