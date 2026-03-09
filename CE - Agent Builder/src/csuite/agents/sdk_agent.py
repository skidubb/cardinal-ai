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
from csuite.prompts.airline_ops_vp_prompt import AIRLINE_OPS_VP_SYSTEM_PROMPT
from csuite.prompts.airport_cio_prompt import AIRPORT_CIO_SYSTEM_PROMPT
from csuite.prompts.airport_cro_prompt import AIRPORT_CRO_SYSTEM_PROMPT
from csuite.prompts.att_carrier_rep_prompt import ATT_CARRIER_REP_SYSTEM_PROMPT
from csuite.prompts.cargo_ops_director_prompt import CARGO_OPS_DIRECTOR_SYSTEM_PROMPT
from csuite.prompts.concessions_tech_lead_prompt import CONCESSIONS_TECH_LEAD_SYSTEM_PROMPT
from csuite.prompts.walk_agents import (
    WALK_ADVERSARIAL_SYSTEM_PROMPT,
    WALK_ANALOGY_SYSTEM_PROMPT,
    WALK_COMPLEXITY_SYSTEM_PROMPT,
    WALK_CONSTRAINT_SYSTEM_PROMPT,
    WALK_ECONOMIST_SYSTEM_PROMPT,
    WALK_FRAMER_SYSTEM_PROMPT,
    WALK_HISTORIAN_SYSTEM_PROMPT,
    WALK_NARRATIVE_SYSTEM_PROMPT,
    WALK_POET_SYSTEM_PROMPT,
    WALK_SALIENCE_JUDGE_SYSTEM_PROMPT,
    WALK_SEMIOTICIAN_SYSTEM_PROMPT,
    WALK_STATISTICIAN_SYSTEM_PROMPT,
    WALK_SYNTHESIZER_SYSTEM_PROMPT,
    WALK_SYSTEMS_SYSTEM_PROMPT,
)
from csuite.prompts.sub_agents import (
    BRAND_ESSENCE_SYSTEM_PROMPT,
    CEO_BOARD_PREP_SYSTEM_PROMPT,
    CEO_COMPETITIVE_INTEL_SYSTEM_PROMPT,
    CEO_DEAL_STRATEGIST_SYSTEM_PROMPT,
    CFO_CASH_FLOW_FORECASTER_SYSTEM_PROMPT,
    CFO_CLIENT_PROFITABILITY_SYSTEM_PROMPT,
    CFO_PRICING_STRATEGIST_SYSTEM_PROMPT,
    CMO_BRAND_DESIGNER_SYSTEM_PROMPT,
    CMO_DISTRIBUTION_STRATEGIST_SYSTEM_PROMPT,
    CMO_LINKEDIN_GHOSTWRITER_SYSTEM_PROMPT,
    CMO_MARKET_INTEL_SYSTEM_PROMPT,
    CMO_OUTBOUND_CAMPAIGN_SYSTEM_PROMPT,
    CMO_THOUGHT_LEADERSHIP_SYSTEM_PROMPT,
    COO_BENCH_COORDINATOR_SYSTEM_PROMPT,
    COO_ENGAGEMENT_MANAGER_SYSTEM_PROMPT,
    COO_PROCESS_BUILDER_SYSTEM_PROMPT,
    CPO_CLIENT_INSIGHTS_SYSTEM_PROMPT,
    CPO_DELIVERABLE_DESIGNER_SYSTEM_PROMPT,
    CPO_SERVICE_DESIGNER_SYSTEM_PROMPT,
    CTO_AI_SYSTEMS_DESIGNER_SYSTEM_PROMPT,
    CTO_AUDIT_ARCHITECT_SYSTEM_PROMPT,
    CTO_INFRA_ENGINEER_SYSTEM_PROMPT,
    CTO_INTERNAL_PLATFORM_SYSTEM_PROMPT,
    CTO_ML_ENGINEER_SYSTEM_PROMPT,
    CTO_RD_LEAD_SYSTEM_PROMPT,
    CTO_SECURITY_ENGINEER_SYSTEM_PROMPT,
    GTM_ABM_SPECIALIST_SYSTEM_PROMPT,
    GTM_AE_STRATEGIST_SYSTEM_PROMPT,
    GTM_ALLIANCE_OPS_SYSTEM_PROMPT,
    GTM_ANALYTICS_SYSTEM_PROMPT,
    GTM_CHANNEL_MARKETER_SYSTEM_PROMPT,
    GTM_CONTENT_MARKETER_SYSTEM_PROMPT,
    GTM_CRO_SYSTEM_PROMPT,
    GTM_CSM_LEAD_SYSTEM_PROMPT,
    GTM_DATA_OPS_SYSTEM_PROMPT,
    GTM_DEAL_DESK_SYSTEM_PROMPT,
    GTM_DEMAND_GEN_SYSTEM_PROMPT,
    GTM_ONBOARDING_SPECIALIST_SYSTEM_PROMPT,
    GTM_PARTNER_ENABLEMENT_SYSTEM_PROMPT,
    GTM_PARTNER_MANAGER_SYSTEM_PROMPT,
    GTM_RENEWALS_MANAGER_SYSTEM_PROMPT,
    GTM_REVENUE_ANALYST_SYSTEM_PROMPT,
    GTM_SALES_OPS_SYSTEM_PROMPT,
    GTM_SDR_AGENT_SYSTEM_PROMPT,
    GTM_SDR_MANAGER_SYSTEM_PROMPT,
    GTM_SYSTEMS_ADMIN_SYSTEM_PROMPT,
    GTM_VP_GROWTH_OPS_SYSTEM_PROMPT,
    GTM_VP_PARTNERSHIPS_SYSTEM_PROMPT,
    GTM_VP_REVOPS_SYSTEM_PROMPT,
    GTM_VP_SALES_SYSTEM_PROMPT,
    GTM_VP_SUCCESS_SYSTEM_PROMPT,
    VC_APP_INVESTOR_SYSTEM_PROMPT,
    VC_INFRA_INVESTOR_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_ROLE_PROMPTS: dict[str, str] = {
    # Executives
    "ceo": CEO_SYSTEM_PROMPT,
    "cfo": CFO_SYSTEM_PROMPT,
    "cto": CTO_SYSTEM_PROMPT,
    "cmo": CMO_SYSTEM_PROMPT,
    "coo": COO_SYSTEM_PROMPT,
    "cpo": CPO_SYSTEM_PROMPT,
    "cro": CRO_SYSTEM_PROMPT,
    # CEO Direct Reports
    "ceo-board-prep": CEO_BOARD_PREP_SYSTEM_PROMPT,
    "ceo-competitive-intel": CEO_COMPETITIVE_INTEL_SYSTEM_PROMPT,
    "ceo-deal-strategist": CEO_DEAL_STRATEGIST_SYSTEM_PROMPT,
    # CFO Direct Reports
    "cfo-cash-flow-forecaster": CFO_CASH_FLOW_FORECASTER_SYSTEM_PROMPT,
    "cfo-client-profitability": CFO_CLIENT_PROFITABILITY_SYSTEM_PROMPT,
    "cfo-pricing-strategist": CFO_PRICING_STRATEGIST_SYSTEM_PROMPT,
    # CMO Direct Reports
    "cmo-brand-designer": CMO_BRAND_DESIGNER_SYSTEM_PROMPT,
    "cmo-distribution-strategist": CMO_DISTRIBUTION_STRATEGIST_SYSTEM_PROMPT,
    "cmo-linkedin-ghostwriter": CMO_LINKEDIN_GHOSTWRITER_SYSTEM_PROMPT,
    "cmo-market-intel": CMO_MARKET_INTEL_SYSTEM_PROMPT,
    "cmo-outbound-campaign": CMO_OUTBOUND_CAMPAIGN_SYSTEM_PROMPT,
    "cmo-thought-leadership": CMO_THOUGHT_LEADERSHIP_SYSTEM_PROMPT,
    # COO Direct Reports
    "coo-bench-coordinator": COO_BENCH_COORDINATOR_SYSTEM_PROMPT,
    "coo-engagement-manager": COO_ENGAGEMENT_MANAGER_SYSTEM_PROMPT,
    "coo-process-builder": COO_PROCESS_BUILDER_SYSTEM_PROMPT,
    # CPO Direct Reports
    "cpo-client-insights": CPO_CLIENT_INSIGHTS_SYSTEM_PROMPT,
    "cpo-deliverable-designer": CPO_DELIVERABLE_DESIGNER_SYSTEM_PROMPT,
    "cpo-service-designer": CPO_SERVICE_DESIGNER_SYSTEM_PROMPT,
    # CTO Direct Reports
    "cto-ai-systems-designer": CTO_AI_SYSTEMS_DESIGNER_SYSTEM_PROMPT,
    "cto-audit-architect": CTO_AUDIT_ARCHITECT_SYSTEM_PROMPT,
    "cto-internal-platform": CTO_INTERNAL_PLATFORM_SYSTEM_PROMPT,
    # CTO R&D Team
    "cto-rd-lead": CTO_RD_LEAD_SYSTEM_PROMPT,
    "cto-ml-engineer": CTO_ML_ENGINEER_SYSTEM_PROMPT,
    "cto-infra-engineer": CTO_INFRA_ENGINEER_SYSTEM_PROMPT,
    "cto-security-engineer": CTO_SECURITY_ENGINEER_SYSTEM_PROMPT,
    # GTM Leadership
    "gtm-cro": GTM_CRO_SYSTEM_PROMPT,
    "gtm-vp-sales": GTM_VP_SALES_SYSTEM_PROMPT,
    "gtm-vp-growth-ops": GTM_VP_GROWTH_OPS_SYSTEM_PROMPT,
    "gtm-vp-partnerships": GTM_VP_PARTNERSHIPS_SYSTEM_PROMPT,
    "gtm-vp-revops": GTM_VP_REVOPS_SYSTEM_PROMPT,
    "gtm-vp-success": GTM_VP_SUCCESS_SYSTEM_PROMPT,
    # GTM Sales & Pipeline
    "gtm-ae-strategist": GTM_AE_STRATEGIST_SYSTEM_PROMPT,
    "gtm-deal-desk": GTM_DEAL_DESK_SYSTEM_PROMPT,
    "gtm-sales-ops": GTM_SALES_OPS_SYSTEM_PROMPT,
    "gtm-sdr-manager": GTM_SDR_MANAGER_SYSTEM_PROMPT,
    "gtm-sdr-agent": GTM_SDR_AGENT_SYSTEM_PROMPT,
    # GTM Marketing & Demand Gen
    "gtm-abm-specialist": GTM_ABM_SPECIALIST_SYSTEM_PROMPT,
    "gtm-content-marketer": GTM_CONTENT_MARKETER_SYSTEM_PROMPT,
    "gtm-demand-gen": GTM_DEMAND_GEN_SYSTEM_PROMPT,
    "gtm-analytics": GTM_ANALYTICS_SYSTEM_PROMPT,
    "gtm-revenue-analyst": GTM_REVENUE_ANALYST_SYSTEM_PROMPT,
    # GTM Partners & Channels
    "gtm-partner-manager": GTM_PARTNER_MANAGER_SYSTEM_PROMPT,
    "gtm-partner-enablement": GTM_PARTNER_ENABLEMENT_SYSTEM_PROMPT,
    "gtm-alliance-ops": GTM_ALLIANCE_OPS_SYSTEM_PROMPT,
    "gtm-channel-marketer": GTM_CHANNEL_MARKETER_SYSTEM_PROMPT,
    # GTM Customer Success & Retention
    "gtm-csm-lead": GTM_CSM_LEAD_SYSTEM_PROMPT,
    "gtm-onboarding-specialist": GTM_ONBOARDING_SPECIALIST_SYSTEM_PROMPT,
    "gtm-renewals-manager": GTM_RENEWALS_MANAGER_SYSTEM_PROMPT,
    # GTM Operations & Infrastructure
    "gtm-data-ops": GTM_DATA_OPS_SYSTEM_PROMPT,
    "gtm-systems-admin": GTM_SYSTEMS_ADMIN_SYSTEM_PROMPT,
    # External Perspectives
    "vc-app-investor": VC_APP_INVESTOR_SYSTEM_PROMPT,
    "vc-infra-investor": VC_INFRA_INVESTOR_SYSTEM_PROMPT,
    "brand-essence": BRAND_ESSENCE_SYSTEM_PROMPT,
    # Walk Protocol Cognitive Lenses
    "walk-framer": WALK_FRAMER_SYSTEM_PROMPT,
    "walk-systems": WALK_SYSTEMS_SYSTEM_PROMPT,
    "walk-analogy": WALK_ANALOGY_SYSTEM_PROMPT,
    "walk-narrative": WALK_NARRATIVE_SYSTEM_PROMPT,
    "walk-constraint": WALK_CONSTRAINT_SYSTEM_PROMPT,
    "walk-adversarial": WALK_ADVERSARIAL_SYSTEM_PROMPT,
    "walk-salience-judge": WALK_SALIENCE_JUDGE_SYSTEM_PROMPT,
    "walk-synthesizer": WALK_SYNTHESIZER_SYSTEM_PROMPT,
    "walk-poet": WALK_POET_SYSTEM_PROMPT,
    "walk-historian": WALK_HISTORIAN_SYSTEM_PROMPT,
    "walk-complexity": WALK_COMPLEXITY_SYSTEM_PROMPT,
    "walk-semiotician": WALK_SEMIOTICIAN_SYSTEM_PROMPT,
    "walk-economist": WALK_ECONOMIST_SYSTEM_PROMPT,
    "walk-statistician": WALK_STATISTICIAN_SYSTEM_PROMPT,
    # Airport 5G Simulation
    "airport-cio": AIRPORT_CIO_SYSTEM_PROMPT,
    "airport-cro": AIRPORT_CRO_SYSTEM_PROMPT,
    "airline-ops-vp": AIRLINE_OPS_VP_SYSTEM_PROMPT,
    "cargo-ops-director": CARGO_OPS_DIRECTOR_SYSTEM_PROMPT,
    "concessions-tech-lead": CONCESSIONS_TECH_LEAD_SYSTEM_PROMPT,
    "att-carrier-rep": ATT_CARRIER_REP_SYSTEM_PROMPT,
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
        from claude_agent_sdk.types import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            ToolResultBlock,
            ToolUseBlock,
        )

        options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            model=self.config.model or get_settings().default_model,
            mcp_servers=self.mcp_servers,
            max_turns=15,
            permission_mode="bypassPermissions",
            cwd=str(get_settings().project_root),
        )

        result_text = ""
        self.tool_calls: list[dict] = []

        async for message in query(prompt=user_message, options=options):
            if isinstance(message, ResultMessage):
                self.cost = message.total_cost_usd or 0.0
                result_text = message.result or ""
            elif isinstance(message, AssistantMessage):
                if not message.content:
                    continue
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        tool_input = block.input
                        # Truncate large inputs for logging
                        input_summary = str(tool_input)[:300] if tool_input else ""
                        self.tool_calls.append({
                            "tool": block.name,
                            "input_summary": input_summary,
                            "id": block.id,
                        })
                        logger.info(
                            "[%s] tool_call: %s | input: %s",
                            self.role, block.name, input_summary[:100],
                        )
                    elif isinstance(block, ToolResultBlock):
                        # Match result back to the call
                        content_preview = str(block.content)[:200] if block.content else ""
                        for tc in reversed(self.tool_calls):
                            if tc["id"] == block.tool_use_id:
                                tc["result_preview"] = content_preview
                                tc["is_error"] = block.is_error
                                break
                        logger.info(
                            "[%s] tool_result: %s | error=%s | preview: %s",
                            self.role, block.tool_use_id,
                            block.is_error, content_preview[:80],
                        )

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
