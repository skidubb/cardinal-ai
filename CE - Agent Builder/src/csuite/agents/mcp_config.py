"""
Per-role MCP server configurations for SDK agents.

Maps each executive role to the MCP servers they need access to.
Custom MCP servers use stdio transport; Notion uses HTTP transport.
Pinecone uses npx-based stdio transport (official plugin).
"""

from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk.types import McpHttpServerConfig, McpStdioServerConfig

McpServerConfig = McpStdioServerConfig | McpHttpServerConfig

# Project root for resolving MCP server paths
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_VENV_PYTHON = str(_PROJECT_ROOT / "venv" / "bin" / "python")


def _custom_server(server_script: str) -> McpStdioServerConfig:
    """Build a stdio MCP server config for a custom server."""
    return McpStdioServerConfig(
        command=_VENV_PYTHON,
        args=[str(_PROJECT_ROOT / "mcp_servers" / server_script)],
    )


# Custom MCP servers (built in mcp_servers/)
SEC_EDGAR = _custom_server("sec_edgar_mcp/server.py")
PRICING_CALCULATOR = _custom_server("pricing_mcp/server.py")
GITHUB_INTEL = _custom_server("github_intel_mcp/server.py")

# Pinecone — Chairman Standing Order: ALL agents get KB access
PINECONE: McpStdioServerConfig = McpStdioServerConfig(
    command="npx",
    args=["-y", "@pinecone-database/mcp"],
    env={"PINECONE_API_KEY": os.environ.get("PINECONE_API_KEY", "")},
)

# Notion — all agents can read/write workspace
NOTION: McpHttpServerConfig = McpHttpServerConfig(
    type="http",
    url="https://mcp.notion.com/mcp",
)

# Shared servers available to all roles
_COMMON: dict[str, McpServerConfig] = {
    "pinecone": PINECONE,
    "notion": NOTION,
}

# Per-role MCP server assignments
ROLE_MCP_SERVERS: dict[str, dict[str, McpServerConfig]] = {
    "ceo": {
        **_COMMON,
    },
    "cfo": {
        **_COMMON,
        "sec-edgar": SEC_EDGAR,
        "pricing-calculator": PRICING_CALCULATOR,
    },
    "cto": {
        **_COMMON,
        "github-intel": GITHUB_INTEL,
    },
    "cmo": {
        **_COMMON,
    },
    "coo": {
        **_COMMON,
    },
    "cpo": {
        **_COMMON,
    },
    "cro": {
        **_COMMON,
        "sec-edgar": SEC_EDGAR,
        "pricing-calculator": PRICING_CALCULATOR,
    },
}


def get_mcp_servers(role: str) -> dict[str, McpServerConfig]:
    """Get MCP server configs for a given role."""
    if role not in ROLE_MCP_SERVERS:
        raise ValueError(f"Unknown role: {role}. Valid: {list(ROLE_MCP_SERVERS)}")
    return ROLE_MCP_SERVERS[role]
