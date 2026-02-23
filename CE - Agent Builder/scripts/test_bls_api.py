#!/usr/bin/env python3
"""
Bureau of Labor Statistics (BLS) API Integration Test/Demo Script.

Demonstrates the BLS client capabilities for prospect research.
Run with: python scripts/test_bls_api.py

Examples tested:
1. Industry employment data
2. Employment trends over time
3. Occupation wage data
4. CPI/inflation data
5. Labor market assessment
6. Available series lookups
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from csuite.tools.bls_api import BLSClient, OCCUPATION_CODES


def format_currency(value: float | int | None) -> str:
    """Format a value as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def format_number(value: int | float | None) -> str:
    """Format a number with commas."""
    if value is None:
        return "N/A"
    return f"{value:,.0f}"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


async def test_industry_employment(client: BLSClient) -> None:
    """Test industry employment data retrieval."""
    print_section("1. Industry Employment Data")

    naics_code = "541512"  # Computer Systems Design
    print(f"\n  Fetching employment data for NAICS {naics_code}...")

    try:
        employment = await client.get_industry_employment(naics_code)
        if employment:
            print(f"  Found {len(employment)} data points")
            print(f"\n  Most recent periods:")
            for emp in employment[:5]:
                print(f"    {emp.period}: {format_number(emp.employment)} employees")
        else:
            print("  No employment data found")
    except Exception as e:
        print(f"  Error: {e}")


async def test_employment_trend(client: BLSClient) -> None:
    """Test employment trend calculation."""
    print_section("2. Employment Trends")

    industries = [
        ("541512", "Computer Systems Design"),
        ("541611", "Management Consulting"),
        ("541613", "Marketing Consulting"),
    ]

    for naics, name in industries:
        print(f"\n  {name} ({naics}):")
        try:
            trend = await client.get_employment_trend(naics)
            if trend:
                print(f"    Direction: {trend.trend_direction}")
                print(f"    Change: {trend.change_percent:+.1f}%")
                print(f"    Current: {format_number(trend.current_employment)}")
                print(f"    Prior: {format_number(trend.prior_employment)}")
                print(f"    Period: {trend.start_period} to {trend.end_period}")
            else:
                print("    Insufficient data for trend analysis")
        except Exception as e:
            print(f"    Error: {e}")


async def test_occupation_wages(client: BLSClient) -> None:
    """Test occupation wage data."""
    print_section("3. Occupation Wages")

    occupations = [
        "15-1252",  # Software Developers
        "13-1111",  # Management Analysts
        "13-1161",  # Market Research Analysts
    ]

    for occ_code in occupations:
        title = OCCUPATION_CODES.get(occ_code, occ_code)
        print(f"\n  {title} ({occ_code}):")
        try:
            wages = await client.get_occupation_wages(occ_code)
            if wages:
                print(f"    Mean Wage: {format_currency(wages.mean_wage)}")
                print(f"    Median Wage: {format_currency(wages.median_wage)}")
                print(f"    Employment: {format_number(wages.employment)}")
            else:
                print("    No wage data available")
        except Exception as e:
            print(f"    Error: {e}")


async def test_cpi_data(client: BLSClient) -> None:
    """Test CPI/inflation data."""
    print_section("4. Consumer Price Index (Inflation)")

    try:
        cpi_data = await client.get_cpi_data()
        if cpi_data:
            print(f"\n  Retrieved {len(cpi_data)} CPI data points")
            print(f"\n  Recent CPI values:")
            for cpi in cpi_data[:6]:
                yoy = f"{cpi.percent_change_from_year_ago:+.1f}%" if cpi.percent_change_from_year_ago else "N/A"
                print(f"    {cpi.period} {cpi.year}: {cpi.value:.1f} (YoY: {yoy})")
        else:
            print("  No CPI data available")
    except Exception as e:
        print(f"  Error: {e}")


async def test_labor_market_assessment(client: BLSClient) -> None:
    """Test labor market assessment."""
    print_section("5. Labor Market Assessment")

    industries = [
        ("541512", "Computer Systems Design"),
        ("541611", "Management Consulting"),
    ]

    for naics, name in industries:
        print(f"\n  {name} ({naics}):")
        try:
            assessment = await client.assess_labor_market(naics)
            if assessment:
                print(f"    Employment Trend: {assessment.employment_trend}")
                print(f"    Wage Level: {assessment.wage_level}")
                print(f"    Market Tightness: {assessment.market_tightness}")
                print(f"\n    Signals:")
                for signal in assessment.signals:
                    print(f"      - {signal}")
                print(f"\n    Opportunities:")
                for opp in assessment.opportunities:
                    print(f"      + {opp}")
            else:
                print("    Unable to generate assessment")
        except Exception as e:
            print(f"    Error: {e}")


async def test_available_series(client: BLSClient) -> None:
    """Show available series lookups."""
    print_section("6. Available Series")

    print("\n  Industries with BLS Series Mappings:")
    industries = client.get_available_industries()
    for naics, series in list(industries.items())[:5]:
        print(f"    {naics}: {series}")

    print("\n  Available Occupation Codes:")
    occupations = client.get_available_occupations()
    for code, title in list(occupations.items())[:5]:
        print(f"    {code}: {title}")


async def main() -> None:
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Bureau of Labor Statistics API Integration Test")
    print("  Cardinal Element - Free API Enrichment Stack")
    print("=" * 60)

    # Initialize client (no API key for testing)
    # For production, pass api_key="your_key" for 500/day limit
    client = BLSClient()

    print("\n  Note: Without API key, limited to 25 queries/day")
    print("  Get free key at: https://data.bls.gov/registrationEngine/")

    try:
        await test_industry_employment(client)
        await test_employment_trend(client)
        await test_occupation_wages(client)
        await test_cpi_data(client)
        await test_labor_market_assessment(client)
        await test_available_series(client)

        print_section("All Tests Complete")
        print("\n  BLS API integration is working correctly.")
        print("  Rate limit: 25 queries/day (500 with free API key)")
        print("  Cost: $0/month")

    except Exception as e:
        print(f"\nError during testing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
