"""
Configuration management for C-Suite agents.

Uses pydantic-settings for environment variable management with validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
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
        role: Literal["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"],
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
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from .env


def get_agent_config(role: str) -> AgentConfig:
    """Get configuration for a specific agent role."""
    if role not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent role: {role}. Valid roles: {list(AGENT_CONFIGS.keys())}")
    return AGENT_CONFIGS[role]
