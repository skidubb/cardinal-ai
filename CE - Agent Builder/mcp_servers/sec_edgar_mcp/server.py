"""SEC EDGAR MCP Server - wraps SECEdgarClient for Claude Code tool use."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mcp.server.fastmcp import FastMCP

from csuite.tools.sec_edgar import SECEdgarClient

mcp = FastMCP("sec-edgar")


def _serialize(obj):
    """Convert dataclass/complex objects to JSON-safe dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return str(obj)


@mcp.tool()
async def search_companies(query: str, limit: int = 10) -> str:
    """Search SEC EDGAR for companies by name. Returns basic company info."""
    client = SECEdgarClient()
    results = await client.search_companies(query, limit=limit)
    return json.dumps([_serialize(r) for r in results], default=str)


@mcp.tool()
async def get_company_financials(cik_or_ticker: str) -> str:
    """Get company financial data (revenue, net income, assets, employees) from SEC XBRL filings.

    Args:
        cik_or_ticker: SEC CIK number or stock ticker (e.g. "AAPL", "320193")
    """
    client = SECEdgarClient()
    result = await client.get_company_financials(cik_or_ticker)
    if not result:
        return json.dumps({"error": f"No financial data found for {cik_or_ticker}"})
    return json.dumps(_serialize(result), default=str)


@mcp.tool()
async def get_recent_filings(
    cik_or_ticker: str,
    form_types: str = "",
    limit: int = 10,
) -> str:
    """Get recent SEC filings for a company.

    Args:
        cik_or_ticker: SEC CIK number or stock ticker
        form_types: Comma-separated form types to filter (e.g. "10-K,10-Q,8-K"). Empty for all.
        limit: Maximum number of filings to return
    """
    client = SECEdgarClient()
    types_list = [t.strip() for t in form_types.split(",") if t.strip()] or None
    results = await client.get_recent_filings(cik_or_ticker, form_types=types_list, limit=limit)
    return json.dumps([_serialize(r) for r in results], default=str)


@mcp.tool()
async def generate_prospect_brief(cik_or_ticker: str) -> str:
    """Generate a prospect research brief with financials, filings, and ICP fit.

    Args:
        cik_or_ticker: SEC CIK number or stock ticker
    """
    client = SECEdgarClient()
    brief = await client.generate_prospect_brief(cik_or_ticker)
    return json.dumps(_serialize(brief), default=str)


if __name__ == "__main__":
    mcp.run()
