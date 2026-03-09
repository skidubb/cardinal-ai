"""
Configuration management for C-Suite agents.

Uses pydantic-settings for environment variable management with validation.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ce_shared.env import find_and_load_dotenv

HAIKU_MODEL = os.getenv("HAIKU_MODEL", "claude-haiku-4-5-20251001")

# Module-level flag to ensure env is loaded exactly once
_env_loaded = False


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic API
    anthropic_api_key: str = Field(..., description="Anthropic API key")

    # Default model for all agents — Opus is mandatory for strategic thinking
    default_model: str = Field(
        default="claude-opus-4-6",
        description=(
            "Default Claude model. C-Suite agents require Opus"
            " for all strategy and analysis."
        ),
    )

    # Google Workspace
    google_credentials_path: Path | None = Field(
        default=None,
        description="Path to Google credentials JSON",
    )

    # GitHub (CTO)
    github_token: str | None = Field(default=None, description="GitHub personal access token")

    # QuickBooks (CFO)
    quickbooks_client_id: str | None = Field(default=None, description="QuickBooks client ID")
    quickbooks_client_secret: str | None = Field(
        default=None, description="QuickBooks client secret"
    )
    quickbooks_refresh_token: str | None = Field(
        default=None, description="QuickBooks refresh token"
    )
    quickbooks_realm_id: str | None = Field(default=None, description="QuickBooks realm ID")

    # OpenAI (Image Generation — CMO/CPO)
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for image generation"
    )

    # Google Gemini (Image Generation — CMO/CPO)
    gemini_api_key: str | None = Field(
        default=None, description="Google Gemini API key for image generation"
    )

    # Pinecone (Knowledge Base)
    pinecone_api_key: str | None = Field(default=None, description="Pinecone API key")
    pinecone_index_host: str | None = Field(
        default=None, description="Pinecone index host URL"
    )
    pinecone_learning_index_host: str | None = Field(
        default=None, description="Pinecone learning/memory index host URL"
    )

    # DuckDB (Memory + Sessions)
    duckdb_path: Path = Field(
        default=Path("./data/agent_memory.duckdb"),
        description="Path to DuckDB database for agent state",
    )
    memory_enabled: bool = Field(default=True, description="Enable agent memory")

    # Tool use
    tools_enabled: bool = Field(default=True, description="Enable agent tool use globally")
    tool_cost_limit: float = Field(
        default=2.50,
        description="Max $ per single chat() call with tools. Aborts tool loop if exceeded.",
    )
    session_cost_limit: float = Field(
        default=5.00,
        description="Max $ per session. Disables tools if exceeded.",
    )

    # Brave Search (Web Search — all agents)
    brave_api_key: str | None = Field(default=None, description="Brave Search API key")

    # Notion (COO primary, all agents read)
    notion_api_key: str | None = Field(default=None, description="Notion integration token")

    # Agent backend: "legacy" (raw Anthropic API) or "sdk" (Claude Agent SDK with MCP)
    agent_backend: str = Field(
        default="legacy",
        description="Agent backend: 'legacy' for raw API, 'sdk' for Agent SDK with MCP tools",
    )

    # Session and reports directories
    session_dir: Path = Field(default=Path("./sessions"), description="Session storage directory")
    reports_dir: Path = Field(default=Path("./reports"), description="Reports output directory")

    # Project root (computed)
    project_root: Path = Field(default=Path("."), description="Project root directory")

    @field_validator("session_dir", "reports_dir", "project_root", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        """Resolve paths to absolute paths."""
        return Path(v).resolve()

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


class AgentConfig:
    """Configuration for individual agents."""

    def __init__(
        self,
        name: str,
        role: str,
        model: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        tools_enabled: bool = True,
    ):
        self.name = name
        self.role = role
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.tools_enabled = tools_enabled


# Agent-specific configurations
# All C-Suite agents use Opus for strategic thinking and analysis.
# Haiku/Sonnet may be used for subordinate tasks, but the primary agent model is always Opus.
AGENT_CONFIGS = {
    "ceo": AgentConfig(
        name="CEO - Chief Executive Officer",
        role="ceo",
        model="claude-opus-4-6",
        temperature=0.6,  # Balanced for strategic reasoning
        max_tokens=8192,
    ),
    "cfo": AgentConfig(
        name="CFO - Chief Financial Officer",
        role="cfo",
        model="claude-opus-4-6",
        temperature=0.5,  # More precise for financial analysis
        max_tokens=8192,
    ),
    "cto": AgentConfig(
        name="CTO - Chief Technology Officer",
        role="cto",
        model="claude-opus-4-6",
        temperature=0.6,  # Balanced for technical reasoning
        max_tokens=8192,
    ),
    "cmo": AgentConfig(
        name="CMO - Chief Marketing Officer",
        role="cmo",
        model="claude-opus-4-6",
        temperature=0.8,  # Higher for strategic creativity
        max_tokens=8192,
    ),
    "coo": AgentConfig(
        name="COO - Chief Operating Officer",
        role="coo",
        model="claude-opus-4-6",
        temperature=0.6,  # Balanced for operational analysis
        max_tokens=8192,
    ),
    "cpo": AgentConfig(
        name="CPO - Chief Product Officer",
        role="cpo",
        model="claude-opus-4-6",
        temperature=0.6,  # Balanced for product strategy
        max_tokens=8192,
    ),
    "cro": AgentConfig(
        name="CRO - Chief Revenue Officer",
        role="cro",
        model="claude-opus-4-6",
        temperature=0.6,  # Balanced for revenue strategy
        max_tokens=8192,
    ),
    # --- CEO Direct Reports ---
    "ceo-board-prep": AgentConfig(
        name="CEO's Board Prep Specialist", role="ceo-board-prep",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "ceo-competitive-intel": AgentConfig(
        name="CEO's Competitive Intelligence Analyst", role="ceo-competitive-intel",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "ceo-deal-strategist": AgentConfig(
        name="CEO's Deal Strategist", role="ceo-deal-strategist",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- CFO Direct Reports ---
    "cfo-cash-flow-forecaster": AgentConfig(
        name="CFO's Cash Flow Forecaster", role="cfo-cash-flow-forecaster",
        model="claude-opus-4-6", temperature=0.5,
    ),
    "cfo-client-profitability": AgentConfig(
        name="CFO's Client Profitability Analyst", role="cfo-client-profitability",
        model="claude-opus-4-6", temperature=0.5,
    ),
    "cfo-pricing-strategist": AgentConfig(
        name="CFO's Pricing Strategist", role="cfo-pricing-strategist",
        model="claude-opus-4-6", temperature=0.5,
    ),
    # --- CMO Direct Reports ---
    "cmo-brand-designer": AgentConfig(
        name="CMO's Brand Designer", role="cmo-brand-designer",
        model="claude-opus-4-6", temperature=0.8,
    ),
    "cmo-distribution-strategist": AgentConfig(
        name="CMO's Distribution Strategist", role="cmo-distribution-strategist",
        model="claude-opus-4-6", temperature=0.8,
    ),
    "cmo-linkedin-ghostwriter": AgentConfig(
        name="CMO's LinkedIn Ghostwriter", role="cmo-linkedin-ghostwriter",
        model="claude-opus-4-6", temperature=0.8,
    ),
    "cmo-market-intel": AgentConfig(
        name="CMO's Market Intelligence Analyst", role="cmo-market-intel",
        model="claude-opus-4-6", temperature=0.8,
    ),
    "cmo-outbound-campaign": AgentConfig(
        name="CMO's Outbound Campaign Specialist", role="cmo-outbound-campaign",
        model="claude-opus-4-6", temperature=0.8,
    ),
    "cmo-thought-leadership": AgentConfig(
        name="CMO's Thought Leadership Director", role="cmo-thought-leadership",
        model="claude-opus-4-6", temperature=0.8,
    ),
    # --- COO Direct Reports ---
    "coo-bench-coordinator": AgentConfig(
        name="COO's Bench Coordinator", role="coo-bench-coordinator",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "coo-engagement-manager": AgentConfig(
        name="COO's Engagement Manager", role="coo-engagement-manager",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "coo-process-builder": AgentConfig(
        name="COO's Process Builder", role="coo-process-builder",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- CPO Direct Reports ---
    "cpo-client-insights": AgentConfig(
        name="CPO's Client Insights Analyst", role="cpo-client-insights",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cpo-deliverable-designer": AgentConfig(
        name="CPO's Deliverable Designer", role="cpo-deliverable-designer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cpo-service-designer": AgentConfig(
        name="CPO's Service Designer", role="cpo-service-designer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- CTO Direct Reports ---
    "cto-ai-systems-designer": AgentConfig(
        name="CTO's AI Systems Designer", role="cto-ai-systems-designer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cto-audit-architect": AgentConfig(
        name="CTO's Audit Architect", role="cto-audit-architect",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cto-internal-platform": AgentConfig(
        name="CTO's Internal Platform Engineer", role="cto-internal-platform",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- CTO R&D Team ---
    "cto-rd-lead": AgentConfig(
        name="CTO's R&D Lead", role="cto-rd-lead",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cto-ml-engineer": AgentConfig(
        name="CTO's ML Engineer", role="cto-ml-engineer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cto-infra-engineer": AgentConfig(
        name="CTO's Infrastructure Engineer", role="cto-infra-engineer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cto-security-engineer": AgentConfig(
        name="CTO's Security & Compliance Engineer", role="cto-security-engineer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- GTM Leadership ---
    "gtm-cro": AgentConfig(
        name="Chief Revenue Officer (GTM)", role="gtm-cro",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-vp-sales": AgentConfig(
        name="VP of Sales", role="gtm-vp-sales",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-vp-growth-ops": AgentConfig(
        name="VP of Growth Ops", role="gtm-vp-growth-ops",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-vp-partnerships": AgentConfig(
        name="VP of Partnerships", role="gtm-vp-partnerships",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-vp-revops": AgentConfig(
        name="VP of Revenue Operations", role="gtm-vp-revops",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-vp-success": AgentConfig(
        name="VP of Customer Success", role="gtm-vp-success",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- GTM Sales & Pipeline ---
    "gtm-ae-strategist": AgentConfig(
        name="AE Strategist", role="gtm-ae-strategist",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-deal-desk": AgentConfig(
        name="Deal Desk", role="gtm-deal-desk",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-sales-ops": AgentConfig(
        name="Sales Ops Analyst", role="gtm-sales-ops",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-sdr-manager": AgentConfig(
        name="SDR Manager", role="gtm-sdr-manager",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-sdr-agent": AgentConfig(
        name="SDR Agent", role="gtm-sdr-agent",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- GTM Marketing & Demand Gen ---
    "gtm-abm-specialist": AgentConfig(
        name="ABM Specialist", role="gtm-abm-specialist",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "gtm-content-marketer": AgentConfig(
        name="Content Marketer", role="gtm-content-marketer",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "gtm-demand-gen": AgentConfig(
        name="Demand Generation Specialist", role="gtm-demand-gen",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "gtm-analytics": AgentConfig(
        name="RevOps Analytics Specialist", role="gtm-analytics",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "gtm-revenue-analyst": AgentConfig(
        name="Revenue Analyst", role="gtm-revenue-analyst",
        model="claude-opus-4-6", temperature=0.7,
    ),
    # --- GTM Partners & Channels ---
    "gtm-partner-manager": AgentConfig(
        name="Partner Manager", role="gtm-partner-manager",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-partner-enablement": AgentConfig(
        name="Partner Enablement Specialist", role="gtm-partner-enablement",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-alliance-ops": AgentConfig(
        name="Alliance Operations Specialist", role="gtm-alliance-ops",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-channel-marketer": AgentConfig(
        name="Channel Marketer", role="gtm-channel-marketer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- GTM Customer Success & Retention ---
    "gtm-csm-lead": AgentConfig(
        name="CSM Lead", role="gtm-csm-lead",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-onboarding-specialist": AgentConfig(
        name="Onboarding Specialist", role="gtm-onboarding-specialist",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-renewals-manager": AgentConfig(
        name="Renewals Manager", role="gtm-renewals-manager",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- GTM Operations & Infrastructure ---
    "gtm-data-ops": AgentConfig(
        name="RevOps Data Operations Specialist", role="gtm-data-ops",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "gtm-systems-admin": AgentConfig(
        name="RevOps Systems Administrator", role="gtm-systems-admin",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- External Perspectives ---
    "vc-app-investor": AgentConfig(
        name="VC App-Layer Investor", role="vc-app-investor",
        model="openai/gpt-4o", temperature=0.6,
    ),
    "vc-infra-investor": AgentConfig(
        name="VC Infra-Layer Investor", role="vc-infra-investor",
        model="gemini/gemini-2.0-flash", temperature=0.6,
    ),
    "brand-essence": AgentConfig(
        name="Brand Essence Analyst", role="brand-essence",
        model="claude-opus-4-6", temperature=0.6,
    ),
    # --- Walk Protocol Cognitive Lenses ---
    "walk-framer": AgentConfig(
        name="Problem Framer", role="walk-framer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-systems": AgentConfig(
        name="Systems Walker", role="walk-systems",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-analogy": AgentConfig(
        name="Analogy Walker", role="walk-analogy",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "walk-narrative": AgentConfig(
        name="Narrative Walker", role="walk-narrative",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "walk-constraint": AgentConfig(
        name="Constraint Walker", role="walk-constraint",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-adversarial": AgentConfig(
        name="Adversarial Walker", role="walk-adversarial",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-salience-judge": AgentConfig(
        name="Salience Judge", role="walk-salience-judge",
        model="claude-opus-4-6", temperature=0.5,
    ),
    "walk-synthesizer": AgentConfig(
        name="Walk Synthesizer", role="walk-synthesizer",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-poet": AgentConfig(
        name="Poet", role="walk-poet",
        model="claude-opus-4-6", temperature=0.8,
    ),
    "walk-historian": AgentConfig(
        name="Historian", role="walk-historian",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-complexity": AgentConfig(
        name="Complexity Researcher", role="walk-complexity",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "walk-semiotician": AgentConfig(
        name="Semiotician", role="walk-semiotician",
        model="claude-opus-4-6", temperature=0.7,
    ),
    "walk-economist": AgentConfig(
        name="Economist", role="walk-economist",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "walk-statistician": AgentConfig(
        name="Statistician", role="walk-statistician",
        model="claude-opus-4-6", temperature=0.5,
    ),
    # --- Airport 5G Decision-Maker Simulation Agents ---
    "airport-cio": AgentConfig(
        name="Airport CIO", role="airport-cio",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "airport-cro": AgentConfig(
        name="Airport CRO", role="airport-cro",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "airline-ops-vp": AgentConfig(
        name="Anchor Airline VP", role="airline-ops-vp",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "cargo-ops-director": AgentConfig(
        name="Cargo Director", role="cargo-ops-director",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "concessions-tech-lead": AgentConfig(
        name="Concessions Tech Lead", role="concessions-tech-lead",
        model="claude-opus-4-6", temperature=0.6,
    ),
    "att-carrier-rep": AgentConfig(
        name="AT&T Carrier Rep", role="att-carrier-rep",
        model="claude-opus-4-6", temperature=0.6,
    ),
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings singleton."""
    global _env_loaded
    if not _env_loaded:
        find_and_load_dotenv(project="agent-builder")
        _env_loaded = True
    return Settings()  # type: ignore[call-arg]  # env vars loaded by ce_shared


def get_agent_config(role: str) -> AgentConfig:
    """Get configuration for a specific agent role."""
    if role not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent role: {role}. Valid roles: {list(AGENT_CONFIGS.keys())}")
    return AGENT_CONFIGS[role]
