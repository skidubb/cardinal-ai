"""Unit tests for ServerAgent per-agent runtime overrides (Phase 1: F4).

Covers: system_prompt override, tool_names override + filtering, tools_available
by model route, and gateway-model chat() dispatch through LiteLLM instead of the
Anthropic client. No real API calls are made anywhere in this file.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from protocols.server_agent import ServerAgent


class TestSystemPromptOverride:
    def test_override_used_verbatim_as_base(self):
        agent = ServerAgent(role="ceo", system_prompt="You are a bespoke test CEO.")
        prompt = agent._build_system_prompt()
        assert prompt.startswith("You are a bespoke test CEO.")

    def test_no_override_falls_back_to_role_prompts(self):
        agent = ServerAgent(role="some-unknown-role-xyz")
        prompt = agent._build_system_prompt()
        # Falls back to BUILTIN_AGENTS or the generic "You are {role}." template.
        assert "some-unknown-role-xyz" in prompt


class TestToolNamesOverride:
    def test_unknown_tool_names_are_dropped_with_warning(self, caplog):
        agent = ServerAgent(
            role="ceo", model="claude-opus-4-8", tool_names=["real_tool", "bogus_tool"]
        )
        fake_schemas = {"real_tool": {"name": "real_tool"}}
        with patch(
            "protocols.server_agent._get_all_tool_schemas", return_value=fake_schemas
        ):
            with caplog.at_level("WARNING"):
                tools = agent._resolve_tools()
        assert tools == [{"name": "real_tool"}]
        assert any("bogus_tool" in r.message for r in caplog.records)

    def test_no_override_uses_role_tool_map(self):
        agent = ServerAgent(role="ceo", model="claude-opus-4-8")
        fake_schemas = {"web_search": {"name": "web_search"}}
        with patch(
            "protocols.server_agent._get_all_tool_schemas", return_value=fake_schemas
        ):
            with patch(
                "protocols.server_agent._get_role_tool_map",
                return_value={"ceo": ["web_search"]},
            ):
                tools = agent._resolve_tools()
        assert tools == [{"name": "web_search"}]

    def test_gateway_model_returns_no_tools_regardless_of_override(self):
        agent = ServerAgent(
            role="ceo", model="deepseek-v4-flash", tool_names=["web_search"]
        )
        tools = agent._resolve_tools()
        assert tools == []


class TestToolsAvailable:
    def test_gateway_model_does_not_support_tools(self):
        agent = ServerAgent(role="ceo", model="deepseek-v4-flash")
        assert agent.tools_available is False

    def test_anthropic_model_supports_tools(self):
        agent = ServerAgent(role="ceo", model="claude-opus-4-8")
        assert agent.tools_available is True


class TestGatewayChatDispatch:
    @pytest.mark.asyncio
    async def test_gateway_model_routes_to_litellm_and_skips_anthropic(self):
        agent = ServerAgent(role="ceo", model="deepseek-v4-flash")

        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

        with patch("litellm.acompletion", new=AsyncMock(return_value=fake_response)):
            result = await agent.chat("question")

        assert result == "hello"
        assert agent.input_tokens == 10
        assert agent.output_tokens == 5
        assert agent.tool_calls == []
        # The Anthropic client is lazily constructed on first access; it must
        # never have been touched for a gateway-routed model.
        assert agent._client is None
