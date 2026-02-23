"""Tests for debate orchestrator — uses mock Anthropic + patched agents."""

from unittest.mock import MagicMock, patch

import pytest

from csuite.debate import DebateOrchestrator
from csuite.prompts.debate_prompt import format_prior_arguments
from csuite.session import DebateArgument, DebateRound, DebateSession
from tests.conftest import make_api_response

# ---------------------------------------------------------------------------
# format_prior_arguments (pure logic)
# ---------------------------------------------------------------------------

class TestFormatPriorArguments:
    def test_empty(self):
        assert format_prior_arguments([]) == "_No prior arguments._"

    def test_single_round(self):
        args = [
            DebateArgument(role="ceo", agent_name="CEO", content="My take", round_number=1),
            DebateArgument(role="cfo", agent_name="CFO", content="My numbers", round_number=1),
        ]
        result = format_prior_arguments(args)
        assert "Round 1" in result
        assert "CEO" in result
        assert "CFO" in result

    def test_multiple_rounds(self):
        args = [
            DebateArgument(role="ceo", agent_name="CEO", content="R1", round_number=1),
            DebateArgument(role="ceo", agent_name="CEO", content="R2", round_number=2),
        ]
        result = format_prior_arguments(args)
        assert "Round 1" in result
        assert "Round 2" in result


# ---------------------------------------------------------------------------
# DebateOrchestrator
# ---------------------------------------------------------------------------

@pytest.fixture
def debate_deps():
    """Patch everything needed to construct DebateOrchestrator and run debates."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = make_api_response(text="Debate synthesis")

    with patch("csuite.debate.get_settings") as mock_gs, \
         patch("csuite.debate.anthropic.Anthropic", return_value=mock_client), \
         patch("csuite.debate.DebateSessionManager") as mock_dsm, \
         patch("csuite.debate.CostTracker"), \
         patch("csuite.debate.Console"), \
         patch("csuite.debate.Progress"), \
         patch("csuite.debate.Markdown"), \
         patch("csuite.debate.Panel"):
        settings = MagicMock()
        settings.anthropic_api_key = "test-key"
        settings.default_model = "claude-opus-4-6"
        mock_gs.return_value = settings
        mock_dsm_instance = MagicMock()
        mock_dsm.return_value = mock_dsm_instance
        yield mock_client, mock_dsm_instance


class TestDebateOrchestrator:
    @pytest.mark.asyncio
    async def test_run_debate_basic(self, debate_deps):
        mock_client, mock_dsm = debate_deps

        async def mock_chat(self, msg, **kw):
            return f"Argument from {self.ROLE}"

        with patch("csuite.agents.base.get_settings") as mock_gs, \
             patch("csuite.agents.base.anthropic.Anthropic"), \
             patch("csuite.agents.base.SessionManager"), \
             patch("csuite.agents.base.MemoryStore"), \
             patch("csuite.agents.base.ExperienceLog"), \
             patch("csuite.agents.base.PreferenceTracker"), \
             patch("csuite.agents.base.BaseAgent.chat", mock_chat):
            s = MagicMock()
            s.anthropic_api_key = "k"
            s.default_model = "claude-opus-4-6"
            s.project_root = MagicMock()
            s.project_root.__truediv__ = MagicMock(
                return_value=MagicMock(exists=MagicMock(return_value=False))
            )
            s.memory_enabled = True
            s.tools_enabled = True
            s.tool_cost_limit = 1.0
            s.session_cost_limit = 5.0
            mock_gs.return_value = s

            orch = DebateOrchestrator()
            orch.client = mock_client
            result = await orch.run_debate(
                question="Should we pivot?",
                roles=["ceo", "cfo"],
                total_rounds=2,
            )
            assert isinstance(result, DebateSession)
            assert len(result.rounds) == 2
            assert result.synthesis == "Debate synthesis"
            assert result.status == "completed"
            # Saved after each round + after synthesis
            assert mock_dsm.save.call_count >= 3

    @pytest.mark.asyncio
    async def test_round_types_correct(self, debate_deps):
        """Opening -> rebuttal(s) -> final."""
        mock_client, mock_dsm = debate_deps

        async def mock_chat(self, msg, **kw):
            return "arg"

        with patch("csuite.agents.base.get_settings") as mock_gs, \
             patch("csuite.agents.base.anthropic.Anthropic"), \
             patch("csuite.agents.base.SessionManager"), \
             patch("csuite.agents.base.MemoryStore"), \
             patch("csuite.agents.base.ExperienceLog"), \
             patch("csuite.agents.base.PreferenceTracker"), \
             patch("csuite.agents.base.BaseAgent.chat", mock_chat):
            s = MagicMock()
            s.anthropic_api_key = "k"
            s.default_model = "claude-opus-4-6"
            s.project_root = MagicMock()
            s.project_root.__truediv__ = MagicMock(
                return_value=MagicMock(exists=MagicMock(return_value=False))
            )
            s.memory_enabled = True
            s.tools_enabled = True
            s.tool_cost_limit = 1.0
            s.session_cost_limit = 5.0
            mock_gs.return_value = s

            orch = DebateOrchestrator()
            orch.client = mock_client
            result = await orch.run_debate("Q?", roles=["ceo"], total_rounds=3)
            types = [r.round_type for r in result.rounds]
            assert types == ["opening", "rebuttal", "final"]

    def test_format_debate_markdown(self, debate_deps):
        orch = DebateOrchestrator()
        debate = DebateSession(question="Q?", agent_roles=["ceo", "cfo"], total_rounds=1)
        debate.add_round(DebateRound(round_number=1, round_type="opening", arguments=[
            DebateArgument(role="ceo", agent_name="CEO", content="My view", round_number=1),
        ]))
        debate.set_synthesis("Final word")
        md = orch._format_debate_markdown(debate, elapsed=120.0)
        assert "# Executive Debate Transcript" in md
        assert "CEO" in md
        assert "My view" in md
        assert "Final word" in md
        assert "2.0 minutes" in md
