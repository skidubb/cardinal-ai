"""Tests for BaseAgent — the most complex module. Uses full mock stack."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csuite.agents.base import BaseAgent
from tests.conftest import make_api_response, make_tool_use_block


# Concrete subclass for testing
class _TestAgent(BaseAgent):
    ROLE = "ceo"

    def get_system_prompt(self) -> str:
        return "You are a test CEO agent."


def _agent_patches():
    """Context manager that patches all BaseAgent external dependencies."""
    return _AgentPatchContext()


class _AgentPatchContext:
    """Bundles all patches needed to construct a BaseAgent."""

    def __enter__(self):
        self.patches = []
        self.mocks = {}

        pairs = [
            ("csuite.agents.base.get_settings", "settings"),
            ("csuite.agents.base.get_agent_config", "agent_config"),
            ("csuite.agents.base.anthropic.Anthropic", "anthropic"),
            ("csuite.agents.base.SessionManager", "session_mgr"),
            ("csuite.agents.base.MemoryStore", "memory_store"),
            ("csuite.agents.base.ExperienceLog", "experience_log"),
            ("csuite.agents.base.PreferenceTracker", "pref_tracker"),
            ("csuite.agents.base.CostTracker", "cost_tracker"),
        ]
        for target, name in pairs:
            p = patch(target)
            mock = p.start()
            self.patches.append(p)
            self.mocks[name] = mock

        # Configure settings
        s = MagicMock()
        s.anthropic_api_key = "test-key"
        s.default_model = "claude-opus-4-6"
        s.project_root = Path("/tmp/fake_project")
        s.memory_enabled = True
        s.tools_enabled = True
        s.tool_cost_limit = 1.0
        s.session_cost_limit = 5.0
        self.mocks["settings"].return_value = s

        # Configure agent config
        cfg = MagicMock()
        cfg.model = "claude-opus-4-6"
        cfg.max_tokens = 8192
        cfg.temperature = 0.6
        cfg.name = "CEO - Test"
        cfg.tools_enabled = True
        self.mocks["agent_config"].return_value = cfg

        # Configure mock client
        self.mock_client = MagicMock()
        self.mock_client.messages.create.return_value = make_api_response()
        self.mocks["anthropic"].return_value = self.mock_client

        # Session manager returns mock session
        self.mocks["session_mgr"].return_value.create_session.return_value = MagicMock(
            id="test-sess",
            messages=[],
            add_message=MagicMock(),
            get_conversation_history=MagicMock(return_value=[]),
            metadata={},
        )

        # Memory / learning return empty
        self.mocks["memory_store"].return_value.enabled = True
        self.mocks["memory_store"].return_value.retrieve.return_value = []
        self.mocks["experience_log"].return_value.get_lessons.return_value = ""
        self.mocks["experience_log"].return_value.detect_correction = (
            lambda msg: False
        )
        self.mocks["pref_tracker"].return_value.get_preference_context.return_value = ""
        self.mocks["cost_tracker"].return_value._load_records.return_value = []

        return self

    def __exit__(self, *args):
        for p in self.patches:
            p.stop()


class TestLoadBusinessContext:
    def test_reads_claude_md(self, tmp_path):
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True)
        claude_md.write_text("# Business Context")
        with _agent_patches() as ctx:
            ctx.mocks["settings"].return_value.project_root = tmp_path
            agent = _TestAgent()
            assert "Business Context" in agent.business_context

    def test_returns_empty_when_missing(self):
        with _agent_patches() as ctx:
            ctx.mocks["settings"].return_value.project_root = Path("/nonexistent")
            agent = _TestAgent()
            assert agent.business_context == ""


class TestBuildSystemPrompt:
    def test_includes_base_prompt(self):
        with _agent_patches():
            agent = _TestAgent()
            prompt = agent._build_system_prompt()
            assert "test CEO agent" in prompt

    def test_includes_business_context(self, tmp_path):
        claude_md = tmp_path / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True)
        claude_md.write_text("Cardinal Element context")
        with _agent_patches() as ctx:
            ctx.mocks["settings"].return_value.project_root = tmp_path
            agent = _TestAgent()
            prompt = agent._build_system_prompt()
            assert "Cardinal Element context" in prompt

    def test_includes_memories(self):
        with _agent_patches() as ctx:
            ctx.mocks["memory_store"].return_value.retrieve.return_value = [
                {"memory_type": "decision", "summary": "Focus on B2B"}
            ]
            agent = _TestAgent()
            prompt = agent._build_system_prompt(query="strategy")
            assert "Focus on B2B" in prompt

    def test_includes_lessons(self):
        with _agent_patches() as ctx:
            ctx.mocks["experience_log"].return_value.get_lessons.return_value = (
                "- [2026-01-01] Check margins"
            )
            agent = _TestAgent()
            prompt = agent._build_system_prompt()
            assert "Check margins" in prompt

    def test_includes_preferences(self):
        with _agent_patches() as ctx:
            ctx.mocks["pref_tracker"].return_value.get_preference_context.return_value = (
                "Risk tolerance: high"
            )
            agent = _TestAgent()
            prompt = agent._build_system_prompt()
            assert "Risk tolerance: high" in prompt


class TestEstimateResponseCost:
    def test_opus_pricing(self):
        with _agent_patches():
            agent = _TestAgent()
            resp = make_api_response(model="claude-opus-4-6", input_tokens=1000, output_tokens=500)
            cost = agent._estimate_response_cost(resp)
            expected = (1000 * 5.0 / 1e6) + (500 * 25.0 / 1e6)
            assert abs(cost - expected) < 1e-8

    def test_haiku_pricing(self):
        with _agent_patches():
            agent = _TestAgent()
            resp = make_api_response(model="claude-haiku-4-5", input_tokens=1000, output_tokens=500)
            cost = agent._estimate_response_cost(resp)
            expected = (1000 * 1.0 / 1e6) + (500 * 5.0 / 1e6)
            assert abs(cost - expected) < 1e-8

    def test_cached_tokens_discounted(self):
        with _agent_patches():
            agent = _TestAgent()
            resp = make_api_response(model="claude-opus-4-6", input_tokens=1000, output_tokens=500)
            resp.usage.cache_read_input_tokens = 400
            cost = agent._estimate_response_cost(resp)
            # 600 non-cached at full rate + 400 at 0.1x
            input_cost = (600 * 5.0 / 1e6) + (400 * 5.0 * 0.1 / 1e6)
            output_cost = 500 * 25.0 / 1e6
            assert abs(cost - (input_cost + output_cost)) < 1e-8


class TestChat:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        with _agent_patches():
            agent = _TestAgent()
            result = await agent.chat("What is the strategy?")
            assert result == "Mock response"
            agent.session.add_message.assert_any_call("user", "What is the strategy?")

    @pytest.mark.asyncio
    async def test_tool_use_loop(self):
        """Mock: first response is tool_use, tool executed, second response is text."""
        with _agent_patches() as ctx:
            tool_resp = make_api_response(
                stop_reason="tool_use",
                content=[make_tool_use_block("test_tool", {"query": "x"}, "tu_1")],
            )
            final_resp = make_api_response(text="Final answer")
            ctx.mock_client.messages.create.side_effect = [tool_resp, final_resp]

            with patch("csuite.agents.base.get_tools_for_role", return_value=[{"name": "test"}]), \
                 patch("csuite.agents.base.execute_tool",
                       new_callable=AsyncMock, return_value='{"result": "ok"}'), \
                 patch.object(BaseAgent, "_post_response_learning"):
                agent = _TestAgent()
                result = await agent.chat("Use a tool")
                assert result == "Final answer"
                assert ctx.mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_max_iterations_guard(self):
        """All responses are tool_use — should stop at MAX_TOOL_ITERATIONS."""
        with _agent_patches() as ctx:
            tool_resp = make_api_response(
                stop_reason="tool_use",
                content=[make_tool_use_block()],
            )
            ctx.mock_client.messages.create.return_value = tool_resp

            with patch("csuite.agents.base.get_tools_for_role", return_value=[{"name": "t"}]), \
                 patch("csuite.agents.base.execute_tool",
                       new_callable=AsyncMock, return_value='{}'), \
                 patch.object(BaseAgent, "_post_response_learning"):
                agent = _TestAgent()
                result = await agent.chat("Infinite tools")
                assert "maximum tool iterations" in result.lower()
                assert ctx.mock_client.messages.create.call_count == BaseAgent.MAX_TOOL_ITERATIONS

    @pytest.mark.asyncio
    async def test_cost_limit_stops_loop(self):
        """Tool loop stops when cost limit is hit."""
        with _agent_patches() as ctx:
            # Make each response very expensive
            tool_resp = make_api_response(
                stop_reason="tool_use",
                content=[make_tool_use_block()],
                input_tokens=500_000,
                output_tokens=200_000,
                model="claude-opus-4-6",
            )
            ctx.mock_client.messages.create.return_value = tool_resp
            ctx.mocks["settings"].return_value.tool_cost_limit = 0.01  # Very low

            with patch("csuite.agents.base.get_tools_for_role", return_value=[{"name": "t"}]), \
                 patch("csuite.agents.base.execute_tool",
                       new_callable=AsyncMock, return_value='{}'), \
                 patch.object(BaseAgent, "_post_response_learning"):
                agent = _TestAgent()
                result = await agent.chat("Expensive tools")
                assert "cost limit" in result.lower()

    @pytest.mark.asyncio
    async def test_saves_session_after_chat(self):
        with _agent_patches() as ctx:
            agent = _TestAgent()
            await agent.chat("Hello")
            ctx.mocks["session_mgr"].return_value.save.assert_called()


class TestShouldUseTools:
    def test_disabled_globally(self):
        with _agent_patches() as ctx:
            ctx.mocks["settings"].return_value.tools_enabled = False
            agent = _TestAgent()
            assert agent._should_use_tools() is False

    def test_disabled_per_agent(self):
        with _agent_patches() as ctx:
            ctx.mocks["agent_config"].return_value.tools_enabled = False
            agent = _TestAgent()
            assert agent._should_use_tools() is False

    def test_disabled_when_session_cost_exceeded(self):
        with _agent_patches() as ctx:
            ctx.mocks["settings"].return_value.session_cost_limit = 0.001
            # Make get_session_cost_summary return high cost
            agent = _TestAgent()
            with patch.object(agent, "get_session_cost_summary", return_value={"total_cost": 10.0}):
                assert agent._should_use_tools() is False


class TestRoleRequired:
    def test_raises_without_role(self):
        with _agent_patches():
            with pytest.raises(ValueError, match="must define ROLE"):

                class _NoRole(BaseAgent):
                    ROLE = ""

                    def get_system_prompt(self):
                        return ""

                _NoRole()
