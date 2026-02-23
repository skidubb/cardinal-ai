"""GitHub Intelligence MCP Server - wraps GitHubClient for Claude Code tool use."""

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mcp.server.fastmcp import FastMCP

from csuite.tools.github_api import GitHubClient

mcp = FastMCP("github-intel")


def _serialize(obj):
    """Convert dataclass/complex objects to JSON-safe dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return str(obj)


def _get_client() -> GitHubClient:
    token = os.environ.get("GITHUB_TOKEN")
    return GitHubClient(token=token)


@mcp.tool()
async def get_organization(org_name: str) -> str:
    """Get GitHub organization info (name, description, repos, members, followers).

    Args:
        org_name: GitHub organization login name (e.g. "stripe", "vercel")
    """
    client = _get_client()
    result = await client.get_organization(org_name)
    if not result:
        return json.dumps({"error": f"Organization '{org_name}' not found"})
    return json.dumps(_serialize(result), default=str)


@mcp.tool()
async def analyze_tech_stack(org_name: str, max_repos: int = 20) -> str:
    """Analyze an organization's tech stack from public GitHub repositories.

    Returns language breakdown, sophistication score, modern/legacy/AI language percentages.

    Args:
        org_name: GitHub organization login name
        max_repos: Maximum repos to analyze (conserves rate limit)
    """
    client = _get_client()
    result = await client.analyze_org_tech_stack(org_name, max_repos=max_repos)
    if not result:
        return json.dumps({"error": f"No repos found for '{org_name}'"})
    return json.dumps(_serialize(result), default=str)


@mcp.tool()
async def assess_engineering_maturity(org_name: str) -> str:
    """Assess engineering maturity of a GitHub organization.

    Checks for CI/CD, testing, documentation, security practices, and AI readiness.

    Args:
        org_name: GitHub organization login name
    """
    client = _get_client()
    result = await client.assess_engineering_maturity(org_name)
    if not result:
        return json.dumps({"error": f"No repos found for '{org_name}'"})
    return json.dumps(_serialize(result), default=str)


if __name__ == "__main__":
    mcp.run()
