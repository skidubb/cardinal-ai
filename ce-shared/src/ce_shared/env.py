"""Environment loading, registry, and validation for the CE-AGENTS monorepo.

Provides:
- ``find_and_load_dotenv()`` -- walk up from CWD to find the monorepo root ``.env``
- ``KEY_REGISTRY`` / ``KeyMeta`` -- canonical inventory of every env var
- ``validate_env()`` -- check required/optional keys, raise on missing required
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

__all__ = [
    "KeyMeta",
    "KEY_REGISTRY",
    "find_and_load_dotenv",
    "validate_env",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyMeta:
    """Describes a single environment variable used in the monorepo."""

    name: str
    required_by: list[str] = field(default_factory=list)
    category: str = "config"
    description: str = ""
    required: bool = False


# ---------------------------------------------------------------------------
# Canonical key registry
# ---------------------------------------------------------------------------

KEY_REGISTRY: dict[str, KeyMeta] = {
    # ---- LLM API keys ----
    "ANTHROPIC_API_KEY": KeyMeta(
        name="ANTHROPIC_API_KEY",
        required_by=["agent-builder", "orchestration", "evals"],
        category="llm",
        description="Anthropic API key (Claude models) -- core dependency for all projects",
        required=True,
    ),
    "OPENAI_API_KEY": KeyMeta(
        name="OPENAI_API_KEY",
        required_by=["agent-builder", "orchestration", "evals"],
        category="llm",
        description="OpenAI API key -- image gen, evals, tool executor",
    ),
    "GOOGLE_API_KEY": KeyMeta(
        name="GOOGLE_API_KEY",
        required_by=["agent-builder", "orchestration", "evals"],
        category="llm",
        description="Google AI (Gemini) API key",
    ),
    "XAI_API_KEY": KeyMeta(
        name="XAI_API_KEY",
        required_by=["agent-builder", "orchestration", "evals"],
        category="llm",
        description="xAI (Grok) API key via LiteLLM",
    ),
    # ---- Observability ----
    "LANGFUSE_SECRET_KEY": KeyMeta(
        name="LANGFUSE_SECRET_KEY",
        required_by=["orchestration"],
        category="observability",
        description="Langfuse secret key for tracing",
    ),
    "LANGFUSE_PUBLIC_KEY": KeyMeta(
        name="LANGFUSE_PUBLIC_KEY",
        required_by=["orchestration"],
        category="observability",
        description="Langfuse public key for tracing",
    ),
    "LANGFUSE_BASE_URL": KeyMeta(
        name="LANGFUSE_BASE_URL",
        required_by=["orchestration"],
        category="observability",
        description="Langfuse server URL (standardized from LANGFUSE_HOST)",
    ),
    # ---- Storage / Database ----
    "DATABASE_URL": KeyMeta(
        name="DATABASE_URL",
        required_by=["orchestration"],
        category="storage",
        description="PostgreSQL connection URL for ce-db",
    ),
    "PINECONE_API_KEY": KeyMeta(
        name="PINECONE_API_KEY",
        required_by=["agent-builder", "orchestration"],
        category="storage",
        description="Pinecone API key for knowledge base and memory",
    ),
    "PINECONE_INDEX_HOST": KeyMeta(
        name="PINECONE_INDEX_HOST",
        required_by=["agent-builder", "orchestration"],
        category="storage",
        description="Pinecone GTM knowledge index host URL",
    ),
    "PINECONE_LEARNING_INDEX_HOST": KeyMeta(
        name="PINECONE_LEARNING_INDEX_HOST",
        required_by=["agent-builder"],
        category="storage",
        description="Pinecone agent memory index host URL",
    ),
    "PINECONE_INDEX": KeyMeta(
        name="PINECONE_INDEX",
        required_by=["orchestration"],
        category="storage",
        description="Pinecone index name (e.g. ce-gtm-knowledge)",
    ),
    "DUCKDB_PATH": KeyMeta(
        name="DUCKDB_PATH",
        required_by=["agent-builder"],
        category="storage",
        description="Path to DuckDB agent memory database",
    ),
    # ---- Search ----
    "BRAVE_API_KEY": KeyMeta(
        name="BRAVE_API_KEY",
        required_by=["agent-builder", "orchestration"],
        category="search",
        description="Brave Search API key for web search tool",
    ),
    # ---- Integrations ----
    "NOTION_API_KEY": KeyMeta(
        name="NOTION_API_KEY",
        required_by=["agent-builder", "orchestration"],
        category="integration",
        description="Notion API key (standardized from NOTION_TOKEN)",
    ),
    "GITHUB_TOKEN": KeyMeta(
        name="GITHUB_TOKEN",
        required_by=["agent-builder", "orchestration"],
        category="integration",
        description="GitHub personal access token for API and MCP server",
    ),
    "DATA_GOV_API_KEY": KeyMeta(
        name="DATA_GOV_API_KEY",
        required_by=["agent-builder"],
        category="integration",
        description="Data.gov API key",
    ),
    "SEC_EDGAR_API_KEY": KeyMeta(
        name="SEC_EDGAR_API_KEY",
        required_by=["agent-builder"],
        category="integration",
        description="SEC EDGAR API key for filing lookups",
    ),
    "US_CENSUS_API_KEY": KeyMeta(
        name="US_CENSUS_API_KEY",
        required_by=["agent-builder"],
        category="integration",
        description="US Census Bureau API key",
    ),
    "US_BLS_API_KEY": KeyMeta(
        name="US_BLS_API_KEY",
        required_by=["agent-builder"],
        category="integration",
        description="US Bureau of Labor Statistics API key",
    ),
    # ---- Config ----
    "MEMORY_ENABLED": KeyMeta(
        name="MEMORY_ENABLED",
        required_by=["agent-builder"],
        category="config",
        description="Toggle memory system (true/false)",
    ),
    "AGENT_BACKEND": KeyMeta(
        name="AGENT_BACKEND",
        required_by=["agent-builder"],
        category="config",
        description="Agent backend: legacy or sdk",
    ),
    "AGENT_MODE": KeyMeta(
        name="AGENT_MODE",
        required_by=["orchestration"],
        category="config",
        description="Agent mode: production or research",
    ),
    # ---- Docker ----
    "POSTGRES_DB": KeyMeta(
        name="POSTGRES_DB",
        required_by=["orchestration"],
        category="docker",
        description="PostgreSQL database name",
    ),
    "POSTGRES_USER": KeyMeta(
        name="POSTGRES_USER",
        required_by=["orchestration"],
        category="docker",
        description="PostgreSQL user",
    ),
    "POSTGRES_PASSWORD": KeyMeta(
        name="POSTGRES_PASSWORD",
        required_by=["orchestration"],
        category="docker",
        description="PostgreSQL password",
    ),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_dotenv() -> Path | None:
    """Walk up from CWD looking for ``.env`` with a ``ce-shared/`` sentinel sibling."""
    current = Path.cwd().resolve()
    for directory in [current, *current.parents]:
        env_path = directory / ".env"
        sentinel = directory / "ce-shared"
        if env_path.is_file() and sentinel.is_dir():
            return env_path
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_env(project: str | None = None) -> list[str]:
    """Check all registry keys against ``os.environ``.

    Parameters
    ----------
    project:
        If provided, only validate keys whose ``required_by`` includes this
        project name (e.g. ``"agent-builder"``).

    Returns
    -------
    list[str]
        Warning messages for missing *optional* keys.

    Raises
    ------
    EnvironmentError
        If any *required* keys are missing, with an actionable message.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for key, meta in KEY_REGISTRY.items():
        # If filtering by project, skip keys not relevant to that project.
        if project is not None and project not in meta.required_by:
            continue

        if key not in os.environ:
            if meta.required:
                errors.append(
                    f"  - {key}: {meta.description}"
                )
            else:
                msg = f"Optional env var {key} is not set ({meta.description})"
                logger.warning(msg)
                warnings.append(msg)

    if errors:
        joined = "\n".join(errors)
        raise EnvironmentError(
            f"Missing required environment variable(s):\n{joined}\n\n"
            "Add to .env at the monorepo root or export in your shell."
        )

    return warnings


def find_and_load_dotenv(project: str | None = None) -> Path | None:
    """Find the monorepo root ``.env``, load it, and validate.

    Parameters
    ----------
    project:
        Passed through to :func:`validate_env` for project-scoped checking.

    Returns
    -------
    Path | None
        The path of the loaded ``.env`` file, or ``None`` if not found.
    """
    path = _find_dotenv()
    if path is not None:
        load_dotenv(str(path), override=False)
        logger.info("Loaded .env from %s", path)
    else:
        logger.info("No monorepo .env found (searched from %s)", Path.cwd())

    validate_env(project)
    return path
