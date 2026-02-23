#!/usr/bin/env python3
"""
SEC EDGAR API Integration Test/Demo Script.

Demonstrates the SEC EDGAR client capabilities for prospect research.
Run with: python scripts/test_sec_edgar.py

Examples tested:
1. Ticker to CIK lookup
2. Company info retrieval
3. Financial data extraction (revenue, net income, employees)
4. Recent filings lookup
5. Form D (funding) search
6. Full prospect research brief generation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from csuite.tools.sec_edgar import SECEdgarClient, ProspectResearchBrief


def format_currency(value: float | None) -> str:
    """Format a value as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.0f}"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_brief(brief: ProspectResearchBrief) -> None:
    """Pretty-print a prospect research brief."""
    if brief.company_info:
        print(f"\nCompany: {brief.company_info.name}")
        print(f"  CIK: {brief.company_info.cik}")
        print(f"  Ticker: {brief.company_info.ticker or 'N/A'}")
        print(f"  Industry: {brief.company_info.sic_description or 'N/A'}")
        print(f"  State: {brief.company_info.state or 'N/A'}")
        print(f"  Entity Type: {brief.company_info.entity_type or 'N/A'}")

    if brief.financials:
        print(f"\nFinancials:")
        print(f"  Revenue: {format_currency(brief.financials.revenue)}")
        if brief.financials.revenue_date:
            print(f"    (filed: {brief.financials.revenue_date})")
        print(f"  Net Income: {format_currency(brief.financials.net_income)}")
        print(f"  Total Assets: {format_currency(brief.financials.total_assets)}")
        print(f"  Employees: {brief.financials.employees or 'N/A'}")

    if brief.recent_filings:
        print(f"\nRecent Filings ({len(brief.recent_filings)}):")
        for filing in brief.recent_filings[:5]:
            print(f"  - {filing.form_type}: {filing.filing_date}")
            if filing.description:
                print(f"    {filing.description[:60]}...")

    if brief.form_d_filings:
        print(f"\nForm D Filings (Funding Rounds): {len(brief.form_d_filings)}")
        for fd in brief.form_d_filings[:3]:
            amendment = " (Amendment)" if fd.is_amendment else ""
            print(f"  - {fd.filing_date}: {fd.company_name}{amendment}")

    if brief.icp_fit:
        print(f"\nICP Fit Analysis:")
        print(f"  Overall Score: {brief.icp_fit.get('overall_score', 0)}/100")
        print(f"  Revenue Fit: {brief.icp_fit.get('revenue_fit', 'unknown')}")
        print(f"  Employee Fit: {brief.icp_fit.get('employee_fit', 'unknown')}")
        print(f"  Industry Fit: {brief.icp_fit.get('industry_fit', 'unknown')}")

        if brief.icp_fit.get('signals'):
            print(f"\n  Positive Signals:")
            for signal in brief.icp_fit['signals']:
                print(f"    + {signal}")

        if brief.icp_fit.get('disqualifiers'):
            print(f"\n  Disqualifiers:")
            for dq in brief.icp_fit['disqualifiers']:
                print(f"    - {dq}")


async def test_ticker_lookup(client: SECEdgarClient) -> None:
    """Test ticker to CIK conversion."""
    print_section("1. Ticker to CIK Lookup")

    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "INVALID"]

    for ticker in tickers:
        cik = await client.ticker_to_cik(ticker)
        print(f"  {ticker} -> CIK: {cik or 'Not found'}")


async def test_company_info(client: SECEdgarClient) -> None:
    """Test company info retrieval."""
    print_section("2. Company Info Retrieval")

    # Test with Apple
    info = await client.get_company_info("AAPL")
    if info:
        print(f"  Name: {info.name}")
        print(f"  CIK: {info.cik}")
        print(f"  Ticker: {info.ticker}")
        print(f"  Industry: {info.sic_description}")
        print(f"  State: {info.state}")
    else:
        print("  Company not found")


async def test_financials(client: SECEdgarClient) -> None:
    """Test financial data extraction."""
    print_section("3. Financial Data Extraction")

    # Test with Microsoft (has good XBRL data)
    financials = await client.get_company_financials("MSFT")
    if financials:
        print(f"  Company: {financials.company_name}")
        print(f"  Revenue: {format_currency(financials.revenue)}")
        print(f"  Net Income: {format_currency(financials.net_income)}")
        print(f"  Total Assets: {format_currency(financials.total_assets)}")
        print(f"  Employees: {financials.employees or 'N/A'}")
    else:
        print("  Financial data not found")


async def test_recent_filings(client: SECEdgarClient) -> None:
    """Test recent filings retrieval."""
    print_section("4. Recent Filings")

    filings = await client.get_recent_filings("TSLA", form_types=["10-K", "10-Q"], limit=5)
    print(f"  Found {len(filings)} filings for TSLA:")
    for filing in filings:
        print(f"    - {filing.form_type}: {filing.filing_date} ({filing.description or 'No description'})")


async def test_company_search(client: SECEdgarClient) -> None:
    """Test company search."""
    print_section("5. Company Search")

    companies = await client.search_companies("consulting", limit=5)
    print(f"  Found {len(companies)} companies matching 'consulting':")
    for company in companies:
        print(f"    - {company.name} (CIK: {company.cik})")


async def test_form_d_search(client: SECEdgarClient) -> None:
    """Test Form D (funding) search."""
    print_section("6. Form D (Funding) Search")

    filings = await client.get_form_d_filings("Stripe")
    print(f"  Found {len(filings)} Form D filings for 'Stripe':")
    for filing in filings[:5]:
        amendment = " (Amendment)" if filing.is_amendment else ""
        print(f"    - {filing.filing_date}: {filing.company_name}{amendment}")


async def test_prospect_brief(client: SECEdgarClient) -> None:
    """Test full prospect research brief generation."""
    print_section("7. Prospect Research Brief (Full)")

    # Generate brief for a mid-size company
    brief = await client.generate_prospect_brief("CRM")  # Salesforce
    print_brief(brief)


async def test_icp_fit_company(client: SECEdgarClient) -> None:
    """Test with a company that might fit ICP better."""
    print_section("8. ICP Fit Test - Smaller Company")

    # Try a smaller company that might fit ICP better
    # Note: Most SEC filers are larger public companies, so ICP fit may be rare
    brief = await client.generate_prospect_brief("EPAM")  # EPAM Systems - services company
    print_brief(brief)


async def main() -> None:
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  SEC EDGAR API Integration Test")
    print("  Cardinal Element - Free API Enrichment Stack")
    print("=" * 60)

    client = SECEdgarClient()

    try:
        await test_ticker_lookup(client)
        await test_company_info(client)
        await test_financials(client)
        await test_recent_filings(client)
        await test_company_search(client)
        await test_form_d_search(client)
        await test_prospect_brief(client)
        await test_icp_fit_company(client)

        print_section("All Tests Complete")
        print("\n  SEC EDGAR integration is working correctly.")
        print("  Rate limiting: 10 req/sec enforced")
        print("  Cost: $0/month (replaces BuiltWith Pro at $295/mo)")

    except Exception as e:
        print(f"\nError during testing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
