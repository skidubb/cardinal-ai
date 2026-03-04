"""Correctness spot-checks for representative protocol outputs.

Goes beyond smoke tests by asserting on output CONTENT — field presence,
agent perspective propagation, winner selection logic, etc.

Uses the same mock infrastructure as test_orchestrator_smoke.py.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Shared mock helpers (same pattern as smoke tests)
# ---------------------------------------------------------------------------

class MockTextBlock:
    type = "text"
    def __init__(self, text: str) -> None:
        self.text = text


class MockUsage:
    input_tokens = 10
    output_tokens = 10


class MockMessage:
    stop_reason = "end_turn"
    def __init__(self, text: str) -> None:
        self.content = [MockTextBlock(text)]
        self.usage = MockUsage()


def _make_mock_client(text: str) -> MagicMock:
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MockMessage(text))
    return client


_TEST_AGENTS = [
    {"name": "agent-alpha", "system_prompt": "You are agent Alpha."},
    {"name": "agent-beta", "system_prompt": "You are agent Beta."},
    {"name": "agent-gamma", "system_prompt": "You are agent Gamma."},
]

_QUESTION = "Should we expand into the European market?"


# ---------------------------------------------------------------------------
# P03 Parallel Synthesis — verify all agent perspectives appear in result
# ---------------------------------------------------------------------------

class TestP03ParallelSynthesisCorrectness:

    def test_all_agent_perspectives_captured(self):
        """Each agent's known response text must appear in the perspectives list."""
        from protocols.p03_parallel_synthesis.orchestrator import SynthesisOrchestrator

        agent_responses = {
            "agent-alpha": "Alpha perspective: focus on Germany first.",
            "agent-beta": "Beta perspective: France offers better margins.",
            "agent-gamma": "Gamma perspective: UK regulatory risk is manageable.",
        }

        async def mock_agent_complete(agent, fallback_model, messages, **kwargs):
            return agent_responses[agent["name"]]

        synthesis_text = "Unified synthesis combining all views."
        mock_client = _make_mock_client(synthesis_text)

        async def _run():
            orch = SynthesisOrchestrator(agents=_TEST_AGENTS)
            orch.client = mock_client
            return await orch.run(_QUESTION)

        with (
            patch("protocols.p03_parallel_synthesis.orchestrator.agent_complete", new=mock_agent_complete),
            patch("protocols.llm.agent_complete", new=mock_agent_complete),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
            patch("protocols.tracing.make_client", return_value=mock_client),
        ):
            result = asyncio.run(_run())

        assert len(result.perspectives) == 3
        perspective_names = {p.name for p in result.perspectives}
        assert perspective_names == {"agent-alpha", "agent-beta", "agent-gamma"}

        for p in result.perspectives:
            assert p.response == agent_responses[p.name], (
                f"Perspective for {p.name} has wrong content"
            )

        assert result.synthesis == synthesis_text
        assert result.question == _QUESTION


# ---------------------------------------------------------------------------
# P06 TRIZ — verify result structure has expected fields
# ---------------------------------------------------------------------------

class TestP06TRIZCorrectness:

    def test_result_structure_has_required_fields(self):
        """TRIZResult must contain failure_modes, solutions, synthesis, and agent_contributions."""
        from protocols.p06_triz.orchestrator import TRIZOrchestrator

        async def mock_agent_complete(agent, fallback_model, messages, **kwargs):
            return f"Failure modes from {agent['name']}: poor logistics"

        dedup_array = json.dumps([{
            "id": 1, "title": "Poor logistics", "description": "Shipping delays",
            "category": "operational",
        }])
        inversion_array = json.dumps([{
            "failure_id": 1, "solution_title": "Build local warehouse",
            "solution_description": "Establish EU distribution center",
        }])
        ranking_array = json.dumps([{
            "failure_id": 1, "severity": 4, "likelihood": 3,
            "composite": 12, "rationale": "High impact",
        }])
        synthesis_text = "Final TRIZ briefing with prioritized solutions."

        responses = [
            MockMessage(dedup_array),
            MockMessage(inversion_array),
            MockMessage(ranking_array),
            MockMessage(synthesis_text),
        ]
        mock_client = _make_mock_client(dedup_array)
        mock_client.messages.create = AsyncMock(side_effect=responses)

        async def _run():
            orch = TRIZOrchestrator(agents=_TEST_AGENTS)
            orch.client = mock_client
            return await orch.run(_QUESTION)

        with (
            patch("protocols.p06_triz.orchestrator.agent_complete", new=mock_agent_complete),
            patch("protocols.llm.agent_complete", new=mock_agent_complete),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
            patch("protocols.tracing.make_client", return_value=mock_client),
        ):
            result = asyncio.run(_run())

        assert result.question == _QUESTION
        assert len(result.failure_modes) == 1
        assert result.failure_modes[0].title == "Poor logistics"
        assert result.failure_modes[0].severity == 4
        assert result.failure_modes[0].composite == 12

        assert len(result.solutions) == 1
        assert result.solutions[0].title == "Build local warehouse"

        assert result.synthesis == synthesis_text

        assert set(result.agent_contributions.keys()) == {
            "agent-alpha", "agent-beta", "agent-gamma"
        }


# ---------------------------------------------------------------------------
# P17 Red/Blue/White — verify adjudication is populated from mock data
# ---------------------------------------------------------------------------

class TestP17RedBlueWhiteCorrectness:

    def test_adjudication_populated(self):
        """Adjudication list must contain entries parsed from the White agent's response."""
        from protocols.p17_red_blue_white.orchestrator import RedBlueWhiteOrchestrator

        red_response = json.dumps({
            "agent": "red-agent",
            "vulnerabilities": [{
                "id": "V1", "title": "Supply chain disruption",
                "severity": "High", "description": "Single supplier risk",
                "failure_scenario": "Supplier goes bankrupt",
            }],
        })
        blue_response = json.dumps({
            "agent": "blue-agent",
            "mitigations": [{
                "vulnerability_id": "V1", "defense_type": "preventive",
                "response": "Dual-source all components",
                "evidence": "Industry best practice", "residual_risk": "low",
            }],
        })
        white_adjudicate = json.dumps({
            "adjudications": [{
                "vulnerability_id": "V1",
                "vulnerability_title": "Supply chain disruption",
                "severity": "High", "verdict": "Resolved",
                "reasoning": "Dual-sourcing mitigates the risk",
                "defense_gaps": "none",
                "recommended_action": "Monitor supplier health quarterly",
            }],
        })
        final_assessment = json.dumps({
            "resolved_risks": [{"id": "V1", "title": "Supply chain disruption"}],
            "open_risks": [],
            "plan_strength_score": 8,
            "recommendations": ["Continue supplier diversification"],
        })

        call_idx = {"n": 0}
        call_responses = (
            [red_response] * 3 + [blue_response] * 3 +
            [white_adjudicate, final_assessment]
        )

        async def mock_agent_complete(agent, fallback_model, messages, **kwargs):
            idx = call_idx["n"]
            call_idx["n"] += 1
            return call_responses[idx]

        mock_client = _make_mock_client(json.dumps({}))

        async def _run():
            orch = RedBlueWhiteOrchestrator(
                red_agents=_TEST_AGENTS,
                blue_agents=_TEST_AGENTS,
                white_agent=_TEST_AGENTS[0],
            )
            orch.client = mock_client
            return await orch.run(_QUESTION, plan="Launch office in Berlin Q3.")

        with (
            patch("protocols.p17_red_blue_white.orchestrator.agent_complete", new=mock_agent_complete),
            patch("protocols.llm.agent_complete", new=mock_agent_complete),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
            patch("protocols.tracing.make_client", return_value=mock_client),
        ):
            result = asyncio.run(_run())

        assert len(result.adjudication) >= 1
        adj = result.adjudication[0]
        assert adj.vulnerability_id == "V1"
        assert adj.verdict == "Resolved"
        assert adj.severity == "High"

        assert result.plan_strength_score == 8
        assert len(result.recommendations) >= 1
        assert len(result.resolved_risks) >= 1
        assert len(result.open_risks) == 0


# ---------------------------------------------------------------------------
# P19 Vickrey Auction — verify winner selection logic
# ---------------------------------------------------------------------------

class TestP19VickreyAuctionCorrectness:

    def test_highest_confidence_wins(self):
        """The agent with the highest confidence bid must be selected as winner."""
        from protocols.p19_vickrey_auction.orchestrator import VickreyOrchestrator

        options = ["Enter Germany first", "Enter France first", "Enter UK first"]

        bid_responses = [
            json.dumps({
                "selected_option": "Enter Germany first",
                "confidence": 90, "reasoning": "Germany has largest GDP",
            }),
            json.dumps({
                "selected_option": "Enter France first",
                "confidence": 75, "reasoning": "France has cultural affinity",
            }),
            json.dumps({
                "selected_option": "Enter Germany first",
                "confidence": 60, "reasoning": "Germany is stable",
            }),
        ]

        calibrated = json.dumps({
            "calibrated_justification": "At 75% confidence, Germany still leads.",
        })
        final = json.dumps({
            "recommendation": "Enter Germany",
            "consensus_score": 0.67,
        })

        call_idx = {"n": 0}
        agent_complete_responses = bid_responses + [calibrated]

        async def mock_agent_complete(agent, fallback_model, messages, **kwargs):
            idx = call_idx["n"]
            call_idx["n"] += 1
            return agent_complete_responses[idx]

        mock_client = _make_mock_client(final)

        async def _run():
            orch = VickreyOrchestrator(agents=_TEST_AGENTS)
            orch.client = mock_client
            return await orch.run(_QUESTION, options=options)

        with (
            patch("protocols.p19_vickrey_auction.orchestrator.agent_complete", new=mock_agent_complete),
            patch("protocols.llm.agent_complete", new=mock_agent_complete),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
            patch("protocols.tracing.make_client", return_value=mock_client),
        ):
            result = asyncio.run(_run())

        assert result.winner == "agent-alpha"
        assert result.winning_option == "Enter Germany first"
        assert result.original_confidence == 90
        assert result.second_price_confidence == 75

        assert len(result.bids) == 3

        assert len(result.bid_distribution["Enter Germany first"]) == 2
        assert len(result.bid_distribution["Enter France first"]) == 1

        assert abs(result.consensus_score - 2 / 3) < 0.01

    def test_single_agent_wins_with_own_confidence(self):
        """With only one agent, winner's confidence equals second price (no second bidder)."""
        from protocols.p19_vickrey_auction.orchestrator import VickreyOrchestrator

        agents = [_TEST_AGENTS[0]]
        options = ["Option A", "Option B"]

        bid = json.dumps({
            "selected_option": "Option A", "confidence": 80,
            "reasoning": "Best option",
        })
        calibrated = json.dumps({
            "calibrated_justification": "High confidence justified.",
        })
        final = json.dumps({"recommendation": "Option A"})

        call_idx = {"n": 0}
        agent_responses = [bid, calibrated]

        async def mock_agent_complete(agent, fallback_model, messages, **kwargs):
            idx = call_idx["n"]
            call_idx["n"] += 1
            return agent_responses[idx]

        mock_client = _make_mock_client(final)

        async def _run():
            orch = VickreyOrchestrator(agents=agents)
            orch.client = mock_client
            return await orch.run(_QUESTION, options=options)

        with (
            patch("protocols.p19_vickrey_auction.orchestrator.agent_complete", new=mock_agent_complete),
            patch("protocols.llm.agent_complete", new=mock_agent_complete),
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
            patch("protocols.tracing.make_client", return_value=mock_client),
        ):
            result = asyncio.run(_run())

        assert result.winner == "agent-alpha"
        assert result.original_confidence == 80
        assert result.second_price_confidence == 80
