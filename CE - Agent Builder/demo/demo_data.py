"""
Pre-cached Demo Data for ODSC AI East 2026 and Discovery Calls.

CTO Sprint 2 Deliverable 5: ODSC Demo Environment.

Contains pre-loaded example companies so demos do not depend on live API calls.
This eliminates the risk of API failures during conference talks or prospect calls.

Companies selected to demonstrate ICP scoring across the spectrum:
1. EPAM Systems -- B2B services company, good ICP fit signal
2. Accenture (ACN) -- Large consulting, above ICP range
3. Apple (AAPL) -- Consumer tech, poor ICP fit (contrast case)
"""

from csuite.tools.sec_edgar import CompanyInfo, FinancialData


# ============================================================================
# Pre-cached Company Data
# ============================================================================

DEMO_COMPANIES: dict[str, dict] = {
    "EPAM": {
        "company_info": CompanyInfo(
            cik="0001352010",
            name="EPAM Systems, Inc.",
            ticker="EPAM",
            sic="7371",
            sic_description="SERVICES-COMPUTER PROGRAMMING, DATA PROCESSING, ETC.",
            state="PA",
            fiscal_year_end="1231",
            entity_type="operating",
        ),
        "financials": FinancialData(
            cik="0001352010",
            company_name="EPAM Systems, Inc.",
            revenue=3_690_000_000,
            revenue_date="2025-02-28",
            net_income=262_000_000,
            net_income_date="2025-02-28",
            total_assets=5_800_000_000,
            total_assets_date="2025-02-28",
            employees=52700,
            employees_date="2025-02-28",
            fiscal_year="2024",
            currency="USD",
        ),
        "narrative": (
            "EPAM is a global IT services company -- a B2B operator at massive scale. "
            "While above CE's ICP range on revenue and headcount, they represent the "
            "kind of company our ICP clients aspire to become. Good demo of the scoring "
            "engine showing 'above range' signals."
        ),
    },
    "ACN": {
        "company_info": CompanyInfo(
            cik="0001467373",
            name="Accenture plc",
            ticker="ACN",
            sic="7389",
            sic_description="SERVICES-MISC BUSINESS SERVICES NEC",
            state="None",
            fiscal_year_end="0831",
            entity_type="operating",
        ),
        "financials": FinancialData(
            cik="0001467373",
            company_name="Accenture plc",
            revenue=64_111_000_000,
            revenue_date="2024-10-17",
            net_income=7_264_000_000,
            net_income_date="2024-10-17",
            total_assets=51_790_000_000,
            total_assets_date="2024-10-17",
            employees=774000,
            employees_date="2024-10-17",
            fiscal_year="2024",
            currency="USD",
        ),
        "narrative": (
            "Accenture is the world's largest professional services company. "
            "Way above ICP range on every dimension. Shows the scoring engine "
            "correctly identifying 'revenue above target' and 'employees above target' "
            "while still recognizing the B2B services industry fit."
        ),
    },
    "AAPL": {
        "company_info": CompanyInfo(
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            sic="3571",
            sic_description="ELECTRONIC COMPUTERS",
            state="CA",
            fiscal_year_end="0930",
            entity_type="operating",
        ),
        "financials": FinancialData(
            cik="0000320193",
            company_name="Apple Inc.",
            revenue=391_035_000_000,
            revenue_date="2024-11-01",
            net_income=93_736_000_000,
            net_income_date="2024-11-01",
            total_assets=364_980_000_000,
            total_assets_date="2024-11-01",
            employees=164000,
            employees_date="2024-11-01",
            fiscal_year="2024",
            currency="USD",
        ),
        "narrative": (
            "Apple is a consumer electronics company -- not a B2B operator. "
            "Shows the scoring engine correctly identifying poor ICP fit: "
            "wrong industry, wrong scale, wrong business model. "
            "Useful contrast case in presentations."
        ),
    },
}


# ============================================================================
# Demo Agent Responses (pre-generated for offline presentations)
# ============================================================================

DEMO_AGENT_RESPONSES: dict[str, dict[str, str]] = {
    "EPAM": {
        "CFO": (
            "## Financial Assessment: EPAM Systems\n\n"
            "**Revenue Profile:** $3.69B annual revenue places EPAM well above "
            "Cardinal Element's target ICP range ($5-40M). However, EPAM's financial "
            "structure is instructive for understanding the services business model "
            "at scale.\n\n"
            "**Key Metrics:**\n"
            "- Revenue: $3.69B (FY2024)\n"
            "- Net Income: $262M (7.1% margin)\n"
            "- Employees: 52,700\n"
            "- Revenue per employee: ~$70K\n\n"
            "**Margin Analysis:** The 7.1% net margin is typical for IT services "
            "companies. For comparison, Cardinal Element targets 80%+ gross margins "
            "by replacing human labor with AI agents -- a fundamentally different "
            "cost structure.\n\n"
            "**ICP Relevance:** While EPAM itself is not an ICP target, their mid-market "
            "competitors ($5-40M revenue) face the same margin pressure with fewer "
            "resources to invest in AI transformation. That is Cardinal Element's sweet spot."
        ),
        "CTO": (
            "## Technical Assessment: EPAM Systems\n\n"
            "**Architecture Opportunity:** EPAM is a technology services company with "
            "52,700 engineers. Their public GitHub presence and technology footprint "
            "suggest a mature engineering organization.\n\n"
            "**Key Technical Signals:**\n"
            "- Primary focus: custom software development, platform engineering\n"
            "- Strong cloud and DevOps capabilities\n"
            "- Active in AI/ML consulting (potential competitor in large enterprise)\n\n"
            "**Growth Architecture Angle:** EPAM's mid-market competitors -- smaller "
            "IT services firms with 50-150 employees -- often lack the engineering "
            "leadership to evaluate and adopt AI effectively. They know they need AI "
            "but do not have a CTO-level resource to architect the transformation.\n\n"
            "**Recommendation:** Use EPAM as a reference case when speaking with "
            "smaller services firms. 'EPAM has 52,000 engineers investing in AI. "
            "How is your 75-person team keeping up?'"
        ),
    },
    "ACN": {
        "CFO": (
            "## Financial Assessment: Accenture plc\n\n"
            "**Revenue Profile:** $64.1B annual revenue -- Accenture is the gold standard "
            "for professional services at scale. Not an ICP target, but the benchmark "
            "every services firm is measured against.\n\n"
            "**Key Metrics:**\n"
            "- Revenue: $64.1B (FY2024)\n"
            "- Net Income: $7.26B (11.3% margin)\n"
            "- Employees: 774,000\n"
            "- Revenue per employee: ~$83K\n\n"
            "**Strategic Insight:** Accenture's $3B+ annual investment in AI and automation "
            "creates a trickle-down effect. Their mid-market competitors see Accenture "
            "winning deals with AI-augmented delivery and feel pressure to match -- but "
            "cannot invest at that scale. Cardinal Element fills this gap."
        ),
        "CTO": (
            "## Technical Assessment: Accenture plc\n\n"
            "**Scale Context:** Accenture has 774,000 employees and invests over "
            "$1B annually in internal technology and AI capabilities. They are not "
            "a prospect -- they are the competitive pressure that drives our ICP "
            "to seek help.\n\n"
            "**Market Signal:** Accenture's AI-first strategy announcement has raised "
            "the bar for every professional services firm. Mid-market operators ($5-40M) "
            "cannot match this investment but their clients increasingly expect AI-augmented "
            "delivery.\n\n"
            "**Cardinal Element Positioning:** We are not competing with Accenture. "
            "We are helping their smaller competitors survive and thrive by providing "
            "AI architecture consulting that would otherwise require a full-time CTO hire "
            "at $300K+/year."
        ),
    },
    "AAPL": {
        "CFO": (
            "## Financial Assessment: Apple Inc.\n\n"
            "**ICP Fit: Poor** -- Apple is a consumer electronics and services company, "
            "not a B2B operator. This analysis demonstrates how the ICP scoring engine "
            "correctly identifies non-target companies.\n\n"
            "**Key Metrics:**\n"
            "- Revenue: $391B (FY2024)\n"
            "- Net Income: $93.7B (24% margin)\n"
            "- Employees: 164,000\n\n"
            "**Why Not ICP:**\n"
            "1. Not a B2B operator (consumer products and services)\n"
            "2. Revenue far exceeds $40M target range\n"
            "3. Industry (electronic computers) is not a services vertical\n"
            "4. Does not have the pain points Cardinal Element solves\n\n"
            "**Demo Note:** This is a useful contrast case showing that the scoring "
            "engine does not just flag everything as a fit."
        ),
        "CTO": (
            "## Technical Assessment: Apple Inc.\n\n"
            "**ICP Fit: Poor** -- Apple is not a B2B operator and does not match "
            "Cardinal Element's target profile on any dimension.\n\n"
            "**Technical Context:**\n"
            "- Apple's engineering organization is world-class and fully self-sufficient\n"
            "- They do not need external AI consulting\n"
            "- Their technology decisions are made by a deep bench of internal leadership\n\n"
            "**Why This Matters for Demo:** Including a well-known non-fit company "
            "demonstrates that the ICP scoring is discriminating, not just rubber-stamping "
            "everything. When a prospect sees Apple scored as 'Poor Fit,' they trust "
            "that a 'Good Fit' score on their own company means something."
        ),
    },
}


def get_demo_company(ticker: str) -> dict | None:
    """Get pre-cached demo company data.

    Args:
        ticker: Stock ticker (case-insensitive)

    Returns:
        Dictionary with company_info, financials, and narrative,
        or None if not a demo company.
    """
    return DEMO_COMPANIES.get(ticker.upper())


def get_demo_response(ticker: str, agent: str) -> str | None:
    """Get pre-cached agent response for a demo company.

    Args:
        ticker: Stock ticker
        agent: Agent name (CFO, CTO, CMO, COO)

    Returns:
        Pre-generated response string, or None if not available.
    """
    company_responses = DEMO_AGENT_RESPONSES.get(ticker.upper(), {})
    return company_responses.get(agent.upper())


def list_demo_companies() -> list[dict[str, str]]:
    """List available demo companies with descriptions."""
    return [
        {
            "ticker": ticker,
            "name": data["company_info"].name,
            "narrative": data["narrative"],
        }
        for ticker, data in DEMO_COMPANIES.items()
    ]
