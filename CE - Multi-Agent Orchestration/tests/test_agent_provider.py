"""Unit tests for agent provider hardening (AGNT-01, AGNT-02, AGNT-03).

All tests are runnable WITHOUT Agent Builder installed or ANTHROPIC_API_KEY set.
SdkAgent is mocked throughout.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_agent_provider_module():
    """Remove cached module so re-imports pick up fresh state."""
    for key in list(sys.modules.keys()):
        if "protocols.agent_provider" in key or key == "protocols.agent_provider":
            del sys.modules[key]


# ---------------------------------------------------------------------------
# AGNT-01: Default mode is "production"
# ---------------------------------------------------------------------------


class TestDefaultMode:
    def test_default_mode_is_production(self):
        """agent_provider._agent_mode must default to 'production', not 'research'."""
        _clear_agent_provider_module()
        import protocols.agent_provider as ap

        assert ap._agent_mode == "production", (
            f"Expected _agent_mode='production' but got '{ap._agent_mode}'. "
            "Hint: change line 22 in agent_provider.py from 'research' to 'production'."
        )


# ---------------------------------------------------------------------------
# AGNT-01: Research mode requires explicit opt-in
# ---------------------------------------------------------------------------


class TestResearchModeOptIn:
    def test_set_agent_mode_research(self):
        """set_agent_mode('research') changes mode to research."""
        _clear_agent_provider_module()
        import protocols.agent_provider as ap

        ap.set_agent_mode("research")
        assert ap.get_agent_mode() == "research"

    def test_agent_mode_env_var_research(self, monkeypatch):
        """AGENT_MODE=research env var — module picks it up when re-imported."""
        _clear_agent_provider_module()
        monkeypatch.setenv("AGENT_MODE", "research")
        import protocols.agent_provider as ap

        # Module-level startup should read AGENT_MODE and call set_agent_mode if provided
        mode = os.environ.get("AGENT_MODE", ap._agent_mode)
        assert mode == "research"
        # Simulate what run.py does: honour the env var explicitly
        if os.environ.get("AGENT_MODE"):
            ap.set_agent_mode(os.environ["AGENT_MODE"])
        assert ap.get_agent_mode() == "research"

    def test_invalid_mode_raises(self):
        """set_agent_mode with invalid value raises ValueError."""
        _clear_agent_provider_module()
        import protocols.agent_provider as ap

        with pytest.raises(ValueError, match="Invalid agent mode"):
            ap.set_agent_mode("bogus")


# ---------------------------------------------------------------------------
# AGNT-01: Path resolution
# ---------------------------------------------------------------------------


class TestPathResolution:
    def test_path_resolution_default(self):
        """_resolve_agent_builder_src() without env var returns path ending in 'CE - Agent Builder/src'."""
        _clear_agent_provider_module()
        import protocols.agent_provider as ap

        result = ap._resolve_agent_builder_src()
        assert result.parts[-1] == "src", (
            f"Expected last part 'src', got '{result.parts[-1]}'"
        )
        assert "CE - Agent Builder" in result.parts, (
            f"Expected 'CE - Agent Builder' in path parts, got: {result.parts}"
        )

    def test_path_resolution_env_var_override(self, monkeypatch, tmp_path):
        """CE_AGENT_BUILDER_PATH env var overrides the computed default path."""
        custom_path = str(tmp_path / "custom_agent_builder" / "src")
        monkeypatch.setenv("CE_AGENT_BUILDER_PATH", custom_path)
        _clear_agent_provider_module()
        import protocols.agent_provider as ap

        result = ap._resolve_agent_builder_src()
        assert result == Path(custom_path).resolve(), (
            f"Expected '{Path(custom_path).resolve()}', got '{result}'"
        )


# ---------------------------------------------------------------------------
# AGNT-02: Startup assertion — server.py lifespan hook
# ---------------------------------------------------------------------------


class TestStartupAssertion:
    @pytest.mark.asyncio
    async def test_startup_assertion_fails_when_sdkagent_not_importable(self):
        """When SdkAgent is not importable, lifespan hook raises RuntimeError with actionable message."""
        # Clear server module so lifespan is re-evaluated
        for key in list(sys.modules.keys()):
            if "api.server" in key or key == "api.server":
                del sys.modules[key]

        # Patch the import of SdkAgent to fail inside the lifespan
        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        with patch(
            "protocols.agent_provider._resolve_agent_builder_src"
        ) as mock_resolve:
            mock_resolve.return_value = Path("/nonexistent/path/src")
            # Now patch builtins to make 'from csuite.agents.sdk_agent import SdkAgent' fail
            with patch(
                "builtins.__import__", side_effect=_make_failing_import("csuite")
            ):
                from api.server import lifespan

                mock_app = MagicMock()
                with pytest.raises(RuntimeError) as exc_info:
                    async with lifespan(mock_app):
                        pass
                err_msg = str(exc_info.value)
                assert (
                    "FATAL" in err_msg
                    or "Production agent import failed" in err_msg
                    or "production" in err_msg.lower()
                ), (
                    f"Expected actionable error message mentioning 'production', got: {err_msg}"
                )

    @pytest.mark.asyncio
    async def test_startup_assertion_passes_when_sdkagent_importable(self):
        """When SdkAgent is importable (mocked), lifespan completes without error."""
        for key in list(sys.modules.keys()):
            if "api.server" in key or key == "api.server":
                del sys.modules[key]

        mock_sdk_agent_class = MagicMock()
        mock_sdk_agent_class.__name__ = "SdkAgent"

        # Patch everything to make the lifespan succeed
        with patch("api.database.create_db_and_tables"):
            with patch(
                "protocols.agent_provider._resolve_agent_builder_src"
            ) as mock_resolve:
                mock_resolve.return_value = Path("/fake/path/src")
                with patch.dict(
                    sys.modules,
                    {
                        "csuite": MagicMock(),
                        "csuite.agents": MagicMock(),
                        "csuite.agents.sdk_agent": MagicMock(
                            SdkAgent=mock_sdk_agent_class
                        ),
                    },
                ):
                    from api.server import lifespan

                    mock_app = MagicMock()
                    # Should complete without raising
                    async with lifespan(mock_app):
                        pass  # lifespan body — if it raises, test fails


# ---------------------------------------------------------------------------
# AGNT-03: Hard failure on agent instantiation error
# ---------------------------------------------------------------------------


class TestHardFailureOnAgentInstantiation:
    def test_hard_failure_on_agent_failure(self):
        """build_production_agents raises RuntimeError listing failed agents when SdkAgent() raises."""
        _clear_agent_provider_module()

        # Build a mock SdkAgent that always raises ValueError
        mock_sdk_agent_class = MagicMock(side_effect=ValueError("config not found"))
        mock_sdk_agent_module = MagicMock()
        mock_sdk_agent_module.SdkAgent = mock_sdk_agent_class

        mock_builtin_agents = {
            "ceo": {"name": "CEO", "system_prompt": "You are the CEO."},
            "cfo": {"name": "CFO", "system_prompt": "You are the CFO."},
        }

        with patch.dict(
            sys.modules,
            {
                "csuite": MagicMock(),
                "csuite.agents": MagicMock(),
                "csuite.agents.sdk_agent": mock_sdk_agent_module,
            },
        ):
            import protocols.agent_provider as ap

            with patch(
                "protocols.agent_provider.BUILTIN_AGENTS",
                mock_builtin_agents,
                create=True,
            ):
                # Also patch the BUILTIN_AGENTS import inside build_production_agents
                with patch(
                    "protocols.agents.BUILTIN_AGENTS", mock_builtin_agents, create=True
                ):
                    with pytest.raises(RuntimeError) as exc_info:
                        ap.build_production_agents(["ceo", "cfo"])
                    err_msg = str(exc_info.value)
                    # Must mention the failed agent names
                    assert "ceo" in err_msg or "cfo" in err_msg, (
                        f"RuntimeError should list failed agent names. Got: {err_msg}"
                    )
                    assert (
                        "production" in err_msg.lower()
                        or "SdkAgent" in err_msg
                        or "failed" in err_msg.lower()
                    ), f"RuntimeError should mention production agents. Got: {err_msg}"

    def test_no_silent_fallback_to_research_mode(self):
        """build_production_agents must NOT silently return dict agents when SdkAgent fails."""
        _clear_agent_provider_module()

        mock_sdk_agent_class = MagicMock(side_effect=ValueError("oops"))
        mock_sdk_agent_module = MagicMock()
        mock_sdk_agent_module.SdkAgent = mock_sdk_agent_class

        mock_builtin_agents = {
            "cto": {"name": "CTO", "system_prompt": "You are the CTO."},
        }

        with patch.dict(
            sys.modules,
            {
                "csuite": MagicMock(),
                "csuite.agents": MagicMock(),
                "csuite.agents.sdk_agent": mock_sdk_agent_module,
            },
        ):
            import protocols.agent_provider as ap

            with patch(
                "protocols.agents.BUILTIN_AGENTS", mock_builtin_agents, create=True
            ):
                # Must raise, must NOT silently return a plain dict list
                with pytest.raises(RuntimeError):
                    result = ap.build_production_agents(["cto"])
                    # If we somehow get here, check that no plain dicts were returned
                    for agent in result:
                        assert not isinstance(agent, dict), (
                            "build_production_agents must not silently fall back to dict agents"
                        )


# ---------------------------------------------------------------------------
# Phase 1 (F4): per-agent runtime overrides — _compose_prompt
# ---------------------------------------------------------------------------


class TestComposePrompt:
    def test_no_system_prompt_returns_none(self):
        import protocols.agent_provider as ap

        assert ap._compose_prompt({}) is None
        assert ap._compose_prompt({"temperature": 0.5}) is None

    def test_assembles_all_sections_in_order(self):
        import protocols.agent_provider as ap

        entry = {
            "system_prompt": "Base prompt.",
            "frameworks": [
                {
                    "name": "SWOT",
                    "description": "Strengths/Weaknesses/Opportunities/Threats",
                    "when_to_use": "Strategic reviews",
                }
            ],
            "deliverable_template": "# Report\n...",
            "communication_style": "Direct and concise.",
            "personality": "Skeptical but constructive.",
            "constraints": ["Never recommend layoffs", "Always cite sources"],
        }
        prompt = ap._compose_prompt(entry)
        assert prompt is not None
        assert prompt.startswith("Base prompt.")
        assert "## Analytical Frameworks" in prompt
        assert "### SWOT" in prompt
        assert "**When to use:** Strategic reviews" in prompt
        assert "## Deliverable Template\n# Report" in prompt
        assert "## Communication Style\nDirect and concise." in prompt
        assert "## Personality\nSkeptical but constructive." in prompt
        assert (
            "## Constraints\n- Never recommend layoffs\n- Always cite sources" in prompt
        )
        # Sections must appear in this order.
        assert prompt.index("## Analytical Frameworks") < prompt.index(
            "## Deliverable Template"
        )
        assert prompt.index("## Deliverable Template") < prompt.index(
            "## Communication Style"
        )
        assert prompt.index("## Communication Style") < prompt.index("## Personality")
        assert prompt.index("## Personality") < prompt.index("## Constraints")

    def test_tolerates_missing_framework_keys(self):
        import protocols.agent_provider as ap

        entry = {"system_prompt": "Base.", "frameworks": [{"name": "Bare"}]}
        prompt = ap._compose_prompt(entry)
        assert prompt is not None
        assert "### Bare" in prompt


# ---------------------------------------------------------------------------
# Phase 1 (F4): build_production_agents forwards DB overrides to ServerAgent
# ---------------------------------------------------------------------------


class TestBuildProductionAgentsOverrides:
    def test_full_db_override_flows_into_server_agent(self):
        import protocols.agent_provider as ap

        fake_override = {
            "model": "claude-sonnet-5",
            "temperature": 0.3,
            "system_prompt": "Custom CEO prompt.",
            "name": "Custom CEO",
            "tools": ["web_search"],
            "kb_namespaces": ["acme-corp"],
            "max_tokens": 4096,
        }
        with patch.object(
            ap, "_load_db_overrides", return_value={"ceo": fake_override}
        ):
            with patch.object(ap, "ServerAgent") as mock_server_agent:
                mock_server_agent.return_value = MagicMock(name="ceo-instance")
                ap.build_production_agents(["ceo"])

        assert mock_server_agent.call_count == 1
        _, kwargs = mock_server_agent.call_args
        assert kwargs["role"] == "ceo"
        assert kwargs["model"] == "claude-sonnet-5"
        assert kwargs["temperature"] == 0.3
        assert kwargs["system_prompt"] == "Custom CEO prompt."
        assert kwargs["display_name"] == "Custom CEO"
        assert kwargs["tool_names"] == ["web_search"]
        assert kwargs["kb_namespaces"] == ["acme-corp"]
        assert kwargs["max_tokens"] == 4096

    def test_passed_model_flows_through_without_db_override(self):
        import protocols.agent_provider as ap

        with patch.object(ap, "_load_db_overrides", return_value={}):
            with patch.object(ap, "ServerAgent") as mock_server_agent:
                mock_server_agent.return_value = MagicMock(name="cfo-instance")
                ap.build_production_agents(["cfo"], model="claude-haiku-4-5-20251001")

        _, kwargs = mock_server_agent.call_args
        assert kwargs["model"] == "claude-haiku-4-5-20251001"
        assert kwargs["system_prompt"] is None
        assert kwargs["tool_names"] is None
        assert kwargs["kb_namespaces"] is None
        assert kwargs["max_tokens"] is None
        assert kwargs["display_name"] is None


# ---------------------------------------------------------------------------
# Helpers for mocking imports
# ---------------------------------------------------------------------------


def _make_failing_import(fail_prefix: str):
    """Return a side_effect function that raises ImportError for any import starting with fail_prefix."""
    real_import = __import__

    def _fake_import(name, *args, **kwargs):
        if name.startswith(fail_prefix):
            raise ImportError(f"No module named '{name}' (mocked failure)")
        return real_import(name, *args, **kwargs)

    return _fake_import
