"""
Per-role MCP server configurations for SDK agents.

Maps each executive role to the MCP servers they need access to.
Custom MCP servers use stdio transport; Notion uses HTTP transport.
Pinecone uses npx-based stdio transport (official plugin).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from claude_agent_sdk.types import McpHttpServerConfig, McpStdioServerConfig

McpServerConfig = Union[McpStdioServerConfig, McpHttpServerConfig]

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
    # --- CEO Direct Reports (inherit CEO: SEC EDGAR, Census) ---
    "ceo-board-prep": {**_COMMON},
    "ceo-competitive-intel": {**_COMMON},
    "ceo-deal-strategist": {**_COMMON},
    # --- CFO Direct Reports (inherit CFO: SEC EDGAR, Pricing) ---
    "cfo-cash-flow-forecaster": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    "cfo-client-profitability": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    "cfo-pricing-strategist": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    # --- CMO Direct Reports (inherit CMO) ---
    "cmo-brand-designer": {**_COMMON},
    "cmo-distribution-strategist": {**_COMMON},
    "cmo-linkedin-ghostwriter": {**_COMMON},
    "cmo-market-intel": {**_COMMON},
    "cmo-outbound-campaign": {**_COMMON},
    "cmo-thought-leadership": {**_COMMON},
    # --- COO Direct Reports (inherit COO) ---
    "coo-bench-coordinator": {**_COMMON},
    "coo-engagement-manager": {**_COMMON},
    "coo-process-builder": {**_COMMON},
    # --- CPO Direct Reports (inherit CPO) ---
    "cpo-client-insights": {**_COMMON},
    "cpo-deliverable-designer": {**_COMMON},
    "cpo-service-designer": {**_COMMON},
    # --- CTO Direct Reports (inherit CTO: GitHub Intel) ---
    "cto-ai-systems-designer": {**_COMMON, "github-intel": GITHUB_INTEL},
    "cto-audit-architect": {**_COMMON, "github-intel": GITHUB_INTEL},
    "cto-internal-platform": {**_COMMON, "github-intel": GITHUB_INTEL},
    # --- CTO R&D Team (inherit CTO: GitHub Intel) ---
    "cto-rd-lead": {**_COMMON, "github-intel": GITHUB_INTEL},
    "cto-ml-engineer": {**_COMMON, "github-intel": GITHUB_INTEL},
    "cto-infra-engineer": {**_COMMON, "github-intel": GITHUB_INTEL},
    "cto-security-engineer": {**_COMMON, "github-intel": GITHUB_INTEL},
    # --- GTM Leadership (inherit CRO: SEC EDGAR, Pricing) ---
    "gtm-cro": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    "gtm-vp-sales": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    "gtm-vp-growth-ops": {**_COMMON},
    "gtm-vp-partnerships": {**_COMMON},
    "gtm-vp-revops": {**_COMMON},
    "gtm-vp-success": {**_COMMON},
    # --- GTM Sales & Pipeline (CRO subset: SEC, Pricing) ---
    "gtm-ae-strategist": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    "gtm-deal-desk": {**_COMMON, "sec-edgar": SEC_EDGAR, "pricing-calculator": PRICING_CALCULATOR},
    "gtm-sales-ops": {**_COMMON},
    "gtm-sdr-manager": {**_COMMON},
    "gtm-sdr-agent": {**_COMMON},
    # --- GTM Marketing & Demand Gen ---
    "gtm-abm-specialist": {**_COMMON},
    "gtm-content-marketer": {**_COMMON},
    "gtm-demand-gen": {**_COMMON},
    "gtm-analytics": {**_COMMON},
    "gtm-revenue-analyst": {**_COMMON, "sec-edgar": SEC_EDGAR},
    # --- GTM Partners & Channels ---
    "gtm-partner-manager": {**_COMMON},
    "gtm-partner-enablement": {**_COMMON},
    "gtm-alliance-ops": {**_COMMON},
    "gtm-channel-marketer": {**_COMMON},
    # --- GTM Customer Success & Retention ---
    "gtm-csm-lead": {**_COMMON},
    "gtm-onboarding-specialist": {**_COMMON},
    "gtm-renewals-manager": {**_COMMON},
    # --- GTM Operations & Infrastructure ---
    "gtm-data-ops": {**_COMMON},
    "gtm-systems-admin": {**_COMMON},
    # --- External Perspectives ---
    "vc-app-investor": {**_COMMON},
    "vc-infra-investor": {**_COMMON},
    "brand-essence": {**_COMMON},
    # --- Airport 5G Decision-Maker Simulation Agents ---
    "airport-cio": {**_COMMON},
    "airport-cro": {**_COMMON},
    "airline-ops-vp": {**_COMMON},
    "cargo-ops-director": {**_COMMON},
    "concessions-tech-lead": {**_COMMON},
    "att-carrier-rep": {**_COMMON},
}


def get_mcp_servers(role: str) -> dict[str, McpServerConfig]:
    """Get MCP server configs for a given role."""
    if role not in ROLE_MCP_SERVERS:
        raise ValueError(f"Unknown role: {role}. Valid: {list(ROLE_MCP_SERVERS)}")
    return ROLE_MCP_SERVERS[role]
