"""Tests for SdkAgent recursive learning — memory, lessons, preferences in system prompt."""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from csuite.agents.sdk_agent import SdkAgent


def _sdk_agent_patches():
    """Patch external deps so SdkAgent can be instantiated without real services."""
    return _SdkPatchContext()


class _SdkPatchContext:
    def __enter__(self):
        self.patches = []
        self.mocks = {}

        pairs = [
            ("csuite.agents.sdk_agent.get_settings", "settings"),
            ("csuite.agents.sdk_agent.get_agent_config", "agent_config"),
            ("csuite.agents.sdk_agent.get_mcp_servers", "mcp_servers"),
            ("csuite.agents.sdk_agent.ExperienceLog", "experience_log"),
            ("csuite.agents.sdk_agent.MemoryStore", "memory_store"),
            ("csuite.agents.sdk_agent.PreferenceTracker", "pref_tracker"),
        ]
        for target, name in pairs:
            p = patch(target)
            mock = p.start()
            self.patches.append(p)
            self.mocks[name] = mock

        # Settings
        s = MagicMock()
        s.default_model = "claude-opus-4-6"
        s.project_root = MagicMock()
        s.project_root.__str__ = lambda _: "/tmp/fake"
        self.mocks["settings"].return_value = s

        # Agent config
        cfg = MagicMock()
        cfg.model = "claude-opus-4-6"
        cfg.name = "CEO - Test"
        self.mocks["agent_config"].return_value = cfg

        # MCP servers
        self.mocks["mcp_servers"].return_value = {}

        # Defaults: empty returns
        self.mocks["memory_store"].return_value.enabled = True
        self.mocks["memory_store"].return_value.retrieve.return_value = []
        self.mocks["experience_log"].return_value.get_lessons.return_value = ""
        self.mocks["experience_log"].return_value.detect_correction = lambda msg: False
        self.mocks["pref_tracker"].return_value.get_preference_context.return_value = ""

        return self

    def __exit__(self, *args):
        for p in self.patches:
            p.stop()


class TestSdkAgentSystemPrompt:
    def test_system_prompt_includes_memories(self):
        with _sdk_agent_patches() as ctx:
            ctx.mocks["memory_store"].return_value.retrieve.return_value = [
                {"memory_type": "decision", "summary": "Focus on B2B SaaS"}
            ]
            agent = SdkAgent(role="ceo")
            prompt = agent._build_system_prompt(query="growth strategy")
            assert "Institutional Memory" in prompt
            assert "Focus on B2B SaaS" in prompt

    def test_system_prompt_includes_lessons(self):
        with _sdk_agent_patches() as ctx:
            ctx.mocks["experience_log"].return_value.get_lessons.return_value = (
                "- [2026-01-15] Always check unit economics before recommending expansion"
            )
            agent = SdkAgent(role="ceo")
            prompt = agent._build_system_prompt()
            assert "Lessons Learned" in prompt
            assert "unit economics" in prompt

    def test_system_prompt_includes_preferences(self):
        with _sdk_agent_patches() as ctx:
            ctx.mocks["pref_tracker"].return_value.get_preference_context.return_value = (
                "Risk tolerance: high\nPreferred format: bullet points"
            )
            agent = SdkAgent(role="ceo")
            prompt = agent._build_system_prompt()
            assert "User Preferences" in prompt
            assert "Risk tolerance: high" in prompt

    def test_graceful_degradation_memory_failure(self):
        with _sdk_agent_patches() as ctx:
            ctx.mocks["memory_store"].return_value.retrieve.side_effect = RuntimeError("Pinecone down")
            agent = SdkAgent(role="ceo")
            prompt = agent._build_system_prompt(query="test query")
            # Should still return a valid prompt without crashing
            assert prompt  # non-empty
            assert "Institutional Memory" not in prompt

    def test_graceful_degradation_all_failures(self):
        with _sdk_agent_patches() as ctx:
            ctx.mocks["memory_store"].return_value.retrieve.side_effect = RuntimeError("boom")
            ctx.mocks["experience_log"].return_value.get_lessons.side_effect = RuntimeError("boom")
            ctx.mocks["pref_tracker"].return_value.get_preference_context.side_effect = (
                RuntimeError("boom")
            )
            agent = SdkAgent(role="ceo")
            prompt = agent._build_system_prompt(query="test")
            # Should return at least the base prompt
            assert prompt
            assert "Institutional Memory" not in prompt
            assert "Lessons Learned" not in prompt
            assert "User Preferences" not in prompt

    @pytest.mark.asyncio
    async def test_chat_passes_query(self):
        with _sdk_agent_patches():
            agent = SdkAgent(role="ceo")
            spy = MagicMock(return_value="base prompt")
            agent._build_system_prompt = spy

            # Mock the SDK query to return a result
            mock_result = MagicMock()
            mock_result.result = "Test response"
            mock_result.total_cost_usd = 0.01

            async def fake_query(**kwargs):
                yield mock_result

            with patch("csuite.agents.sdk_agent.query", side_effect=fake_query):
                # Import ResultMessage for isinstance check
                with patch(
                    "csuite.agents.sdk_agent.ResultMessage",
                    type(mock_result),
                ):
                    await agent.chat("What growth strategy?")

            spy.assert_called_once_with(query="What growth strategy?")
