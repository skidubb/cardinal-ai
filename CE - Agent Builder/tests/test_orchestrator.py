"""Tests for orchestrator — uses mock Anthropic client + patched agents."""

from unittest.mock import MagicMock, patch

import pytest

from csuite.orchestrator import AgentPerspective, Orchestrator
from tests.conftest import make_api_response


@pytest.fixture
def mock_orchestrator_deps():
    """Patch Settings and Anthropic for Orchestrator construction."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = make_api_response(text="Synthesized recommendation")
    with patch("csuite.orchestrator.get_settings") as mock_gs, \
         patch("csuite.orchestrator.anthropic.Anthropic", return_value=mock_client):
        settings = MagicMock()
        settings.anthropic_api_key = "test-key"
        settings.default_model = "claude-opus-4-6"
        mock_gs.return_value = settings
        yield mock_client, settings


class TestOrchestratorGetAgent:
    def test_returns_correct_agent_class(self, mock_orchestrator_deps):
        # Also need to patch agent construction dependencies
        with patch("csuite.orchestrator.get_settings") as mock_gs, \
             patch("csuite.agents.base.get_settings") as mock_gs2, \
             patch("csuite.agents.base.anthropic.Anthropic"), \
             patch("csuite.agents.base.SessionManager"), \
             patch("csuite.agents.base.MemoryStore"), \
             patch("csuite.agents.base.ExperienceLog"), \
             patch("csuite.agents.base.PreferenceTracker"):
            settings = MagicMock()
            settings.anthropic_api_key = "test-key"
            settings.default_model = "claude-opus-4-6"
            settings.project_root = MagicMock()
            mock_p = MagicMock(exists=MagicMock(return_value=False))
            settings.project_root.__truediv__ = MagicMock(
                return_value=mock_p,
            )
            settings.memory_enabled = True
            settings.tools_enabled = True
            settings.tool_cost_limit = 1.0
            settings.session_cost_limit = 5.0
            mock_gs.return_value = settings
            mock_gs2.return_value = settings

            orch = Orchestrator()
            agent = orch.get_agent("ceo")
            assert agent.ROLE == "ceo"

    def test_raises_on_unknown_role(self, mock_orchestrator_deps):
        orch = Orchestrator()
        with pytest.raises(ValueError, match="Unknown agent role"):
            orch.get_agent("janitor")


class TestQueryAgentsParallel:
    @pytest.mark.asyncio
    async def test_runs_agents_concurrently(self, mock_orchestrator_deps):
        mock_client, settings = mock_orchestrator_deps

        async def mock_chat(self, msg, **kw):
            return f"Response from {self.ROLE}"

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
            mock_p = MagicMock(exists=MagicMock(return_value=False))
            s.project_root.__truediv__ = MagicMock(
                return_value=mock_p,
            )
            s.memory_enabled = True
            s.tools_enabled = True
            s.tool_cost_limit = 1.0
            s.session_cost_limit = 5.0
            mock_gs.return_value = s

            orch = Orchestrator()
            perspectives = await orch.query_agents_parallel(["ceo", "cfo"], "Test question")
            assert len(perspectives) == 2
            roles = {p.role for p in perspectives}
            assert roles == {"ceo", "cfo"}


class TestSynthesizePerspectives:
    def test_calls_api_with_perspectives(self, mock_orchestrator_deps):
        mock_client, settings = mock_orchestrator_deps
        orch = Orchestrator()
        perspectives = [
            AgentPerspective(role="ceo", name="CEO", response="Grow fast"),
            AgentPerspective(role="cfo", name="CFO", response="Watch margins"),
        ]
        result, usage = orch.synthesize_perspectives("What should we do?", perspectives)
        assert result == "Synthesized recommendation"
        assert usage is not None
        assert mock_client.messages.create.called
        call_kwargs = mock_client.messages.create.call_args
        # Verify perspectives are in the prompt
        user_msg = call_kwargs.kwargs.get("messages", call_kwargs[1].get("messages", []))[0]
        assert "Grow fast" in user_msg["content"]
        assert "Watch margins" in user_msg["content"]
