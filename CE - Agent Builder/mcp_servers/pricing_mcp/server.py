"""Pricing Calculator MCP Server - wraps PricingCalculator for Claude Code tool use."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mcp.server.fastmcp import FastMCP

from csuite.tools.pricing_calculator import (
    ComplexityLevel,
    IndustryVertical,
    PricingCalculator,
)

mcp = FastMCP("pricing-calculator")


@mcp.tool()
def calculate_audit_price(
    complexity: str = "standard",
    industry: str = "professional_services",
    timeline_weeks: int = 3,
    client_revenue: float = 0,
) -> str:
    """Calculate pricing for a Growth Strategy Audit ($15-25K range).

    Args:
        complexity: standard, complex, or enterprise
        industry: professional_services, technology, healthcare,
            financial_services, manufacturing, other
        timeline_weeks: Delivery timeline in weeks (standard is 3)
        client_revenue: Client annual revenue for ROI calculation
    """
    calc = PricingCalculator()
    proposal = calc.calculate_audit_price(
        complexity=ComplexityLevel(complexity),
        industry=IndustryVertical(industry),
        timeline_weeks=timeline_weeks,
        client_revenue=client_revenue,
    )
    return json.dumps(proposal.to_dict(), default=str)


@mcp.tool()
def calculate_implementation_price(
    complexity: str = "complex",
    industry: str = "professional_services",
    timeline_weeks: int = 12,
    scope_description: str = "",
    client_revenue: float = 0,
) -> str:
    """Calculate pricing for an Implementation Engagement ($50-150K range).

    Args:
        complexity: standard, complex, or enterprise
        industry: professional_services, technology, healthcare,
            financial_services, manufacturing, other
        timeline_weeks: Delivery timeline in weeks (standard is 12)
        scope_description: Brief description of implementation scope
        client_revenue: Client annual revenue for ROI calculation
    """
    calc = PricingCalculator()
    proposal = calc.calculate_implementation_price(
        complexity=ComplexityLevel(complexity),
        industry=IndustryVertical(industry),
        timeline_weeks=timeline_weeks,
        scope_description=scope_description,
        client_revenue=client_revenue,
    )
    return json.dumps(proposal.to_dict(), default=str)


@mcp.tool()
def calculate_retainer_price(
    complexity: str = "standard",
    industry: str = "professional_services",
    commitment_months: int = 1,
    hours_per_month: int = 10,
    client_revenue: float = 0,
) -> str:
    """Calculate pricing for a Retainer engagement ($10-25K/month range).

    Args:
        complexity: standard, complex, or enterprise
        industry: professional_services, technology, healthcare,
            financial_services, manufacturing, other
        commitment_months: Commitment term (1, 3, 6, or 12 months)
        hours_per_month: Expected advisory hours per month
        client_revenue: Client annual revenue for ROI calculation
    """
    calc = PricingCalculator()
    proposal = calc.calculate_retainer_price(
        complexity=ComplexityLevel(complexity),
        industry=IndustryVertical(industry),
        commitment_months=commitment_months,
        hours_per_month=hours_per_month,
        client_revenue=client_revenue,
    )
    return json.dumps(proposal.to_dict(), default=str)


if __name__ == "__main__":
    mcp.run()
