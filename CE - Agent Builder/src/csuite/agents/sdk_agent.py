"""
SDK Agent adapter — delegates to Claude Agent SDK instead of raw Anthropic API.

Provides the same async chat() -> str interface as BaseAgent but uses
claude_agent_sdk.query() with per-role MCP server access.
"""

from __future__ import annotations

import logging

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from csuite.agents.mcp_config import get_mcp_servers
from csuite.config import AgentConfig, get_agent_config, get_settings
from csuite.prompts import (
    CEO_SYSTEM_PROMPT,
    CFO_SYSTEM_PROMPT,
    CMO_SYSTEM_PROMPT,
    COO_SYSTEM_PROMPT,
    CPO_SYSTEM_PROMPT,
    CRO_SYSTEM_PROMPT,
    CTO_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_ROLE_PROMPTS: dict[str, str] = {
    "ceo": CEO_SYSTEM_PROMPT,
    "cfo": CFO_SYSTEM_PROMPT,
    "cto": CTO_SYSTEM_PROMPT,
    "cmo": CMO_SYSTEM_PROMPT,
    "coo": COO_SYSTEM_PROMPT,
    "cpo": CPO_SYSTEM_PROMPT,
    "cro": CRO_SYSTEM_PROMPT,
}


def _load_business_context() -> str:
    """Load business context from CLAUDE.md."""
    settings = get_settings()
    claude_md = settings.project_root / ".claude" / "CLAUDE.md"
    if claude_md.exists():
        return claude_md.read_text()
    return ""


class SdkAgent:
    """Agent adapter using Claude Agent SDK with MCP tool access.

    Drop-in replacement for BaseAgent in CLI/orchestrator/debate flows.
    Does not subclass BaseAgent — keeps the interface minimal.
    """

    ROLE: str = ""

    def __init__(self, role: str | None = None, cost_tracker=None):
        self.role = role or self.ROLE
        if not self.role:
            raise ValueError("SdkAgent requires a role")
        self.config: AgentConfig = get_agent_config(self.role)
        self.mcp_servers: dict = get_mcp_servers(self.role)  # type: ignore[assignment]
        self.console = Console()
        self.cost: float = 0.0
        self._cost_tracker = cost_tracker

    def _build_system_prompt(self) -> str:
        base = _ROLE_PROMPTS.get(self.role, "")
        ctx = _load_business_context()
        if ctx:
            return f"{base}\n\n## Business Context\n\n{ctx}"
        return base

    async def chat(self, user_message: str, **kwargs) -> str:
        """Send a message and get a response via Agent SDK.

        Accepts **kwargs for compatibility with BaseAgent.chat() callers
        (task_type, audit_id, causal_graph) but ignores them — cost tracking
        is handled natively by the SDK.
        """
        from claude_agent_sdk import query
        from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage

        options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            model=self.config.model or get_settings().default_model,
            mcp_servers=self.mcp_servers,
            max_turns=15,
            permission_mode="bypassPermissions",
            cwd=str(get_settings().project_root),
        )

        result_text = ""
        async for message in query(prompt=user_message, options=options):
            if isinstance(message, ResultMessage):
                self.cost = message.total_cost_usd or 0.0
                result_text = message.result or ""

        if self._cost_tracker and self.cost > 0:
            record = self._cost_tracker.log_usage(
                agent=self.role,
                model=self.config.model or get_settings().default_model,
                input_tokens=0,
                output_tokens=0,
                metadata={"sdk_cost_usd": self.cost},
            )
            # Override computed cost (0 from tokens) with SDK-reported cost
            record.total_cost = self.cost

        if not result_text:
            result_text = "[SDK agent returned no result]"

        return result_text

    def display_response(self, response: str) -> None:
        """Display a response with rich formatting."""
        self.console.print()
        self.console.print(
            Panel(
                Markdown(response),
                title=f"[bold blue]{self.config.name}[/bold blue]",
                border_style="blue",
            )
        )
        self.console.print()

    def get_session_id(self) -> str:
        return "sdk-session"
