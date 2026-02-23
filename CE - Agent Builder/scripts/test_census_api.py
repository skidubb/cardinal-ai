#!/usr/bin/env python3
"""
Census Bureau API Integration Test/Demo Script.

Demonstrates the Census Bureau client capabilities for prospect research.
Run with: python scripts/test_census_api.py

Examples tested:
1. Industry benchmarks (national level)
2. State-level business data
3. ZIP code lookups
4. Market size estimation
5. Prospect benchmarking against industry
6. Top states for an industry
7. NAICS code lookup
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from csuite.tools.census_api import CensusClient, ICP_NAICS_CODES


def format_currency(value: float | int | None) -> str:
    """Format a value as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
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


async def test_industry_benchmarks(client: CensusClient) -> None:
    """Test national industry benchmarks."""
    print_section("1. Industry Benchmarks (National)")

    # Test with a few ICP-relevant industries
    test_industries = [
        ("541512", "Computer Systems Design"),
        ("541611", "Management Consulting"),
        ("541613", "Marketing Consulting"),
    ]

    for naics, name in test_industries:
        benchmarks = await client.get_industry_benchmarks(naics)
        if benchmarks:
            print(f"\n  {name} ({naics}):")
            print(f"    Establishments: {format_number(benchmarks.establishments)}")
            print(f"    Total Employees: {format_number(benchmarks.total_employees)}")
            print(f"    Total Payroll: {format_currency(benchmarks.total_payroll * 1000)}")
            print(f"    Avg Employees/Firm: {benchmarks.avg_employees_per_firm:.1f}")
            print(f"    Avg Payroll/Employee: {format_currency(benchmarks.avg_payroll_per_employee)}")
        else:
            print(f"\n  {name} ({naics}): No data available")


async def test_state_data(client: CensusClient) -> None:
    """Test state-level business data."""
    print_section("2. State-Level Business Data")

    naics = "541512"  # Computer Systems Design
    states = ["CA", "TX", "NY", "FL"]

    print(f"\n  Computer Systems Design by State:")
    for state in states:
        data = await client.get_state_business_data(naics, state)
        if data:
            print(f"    {state}: {format_number(data.establishments)} firms, "
                  f"{format_number(data.employees)} employees")
        else:
            print(f"    {state}: No data")


async def test_zip_code_data(client: CensusClient) -> None:
    """Test ZIP code lookups."""
    print_section("3. ZIP Code Business Data")

    naics = "541611"  # Management Consulting
    zip_codes = ["10001", "94105", "60601"]  # NYC, SF, Chicago

    print(f"\n  Management Consulting by ZIP Code:")
    for zip_code in zip_codes:
        data = await client.get_zip_code_data(zip_code, naics)
        if data:
            emp_str = format_number(data.employees) if data.employees else "suppressed"
            print(f"    {zip_code}: {format_number(data.establishments)} firms, "
                  f"{emp_str} employees")
        else:
            print(f"    {zip_code}: No data")


async def test_market_size(client: CensusClient) -> None:
    """Test market size estimation."""
    print_section("4. Market Size Estimation")

    naics = "541613"  # Marketing Consulting

    # National
    national = await client.estimate_market_size(naics)
    if national:
        print(f"\n  Marketing Consulting - National:")
        print(f"    Total Establishments: {format_number(national.total_establishments)}")
        print(f"    Total Employees: {format_number(national.total_employees)}")
        print(f"    Est. Market Size: {format_currency(national.estimated_revenue)}")
        print(f"    Market Concentration: {national.market_concentration}")

    # California only
    ca = await client.estimate_market_size(naics, "CA")
    if ca:
        print(f"\n  Marketing Consulting - California:")
        print(f"    Total Establishments: {format_number(ca.total_establishments)}")
        print(f"    Total Employees: {format_number(ca.total_employees)}")
        print(f"    Est. Market Size: {format_currency(ca.estimated_revenue)}")


async def test_prospect_benchmark(client: CensusClient) -> None:
    """Test prospect benchmarking."""
    print_section("5. Prospect Benchmarking")

    # Simulate three different prospect sizes
    prospects = [
        (15, "541512", "Small tech services firm"),
        (75, "541611", "Mid-size consulting firm"),
        (200, "541613", "Large marketing agency"),
    ]

    for employees, naics, desc in prospects:
        benchmark = await client.benchmark_prospect(employees, naics)
        if benchmark:
            print(f"\n  {desc} ({employees} employees):")
            print(f"    Industry Avg: {benchmark.industry_avg_employees:.0f} employees")
            print(f"    Size Percentile: {benchmark.size_percentile}")
            print(f"    ICP Fit: {'Yes' if benchmark.icp_fit else 'No'}")
            print(f"    Signals:")
            for signal in benchmark.signals:
                print(f"      - {signal}")


async def test_top_states(client: CensusClient) -> None:
    """Test top states for an industry."""
    print_section("6. Top States by Industry")

    naics = "541512"  # Computer Systems Design

    top_states = await client.get_top_states_for_industry(naics, limit=5)
    if top_states:
        print(f"\n  Top 5 States for Computer Systems Design:")
        for i, state in enumerate(top_states, 1):
            print(f"    {i}. {state.state_name}: {format_number(state.establishments)} firms, "
                  f"{format_number(state.employees)} employees")


async def test_naics_lookup(client: CensusClient) -> None:
    """Test NAICS code lookup."""
    print_section("7. NAICS Code Lookup")

    search_terms = ["consulting", "engineering", "advertising"]

    for term in search_terms:
        matches = client.lookup_naics_code(term)
        print(f"\n  Search: '{term}'")
        if matches:
            for code, desc in matches:
                print(f"    {code}: {desc}")
        else:
            print("    No matches found")


async def test_icp_industries(client: CensusClient) -> None:
    """Show all ICP target industries."""
    print_section("8. ICP Target Industries")

    print("\n  Cardinal Element ICP NAICS Codes:")
    for code, desc in sorted(ICP_NAICS_CODES.items()):
        print(f"    {code}: {desc}")


async def main() -> None:
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Census Bureau API Integration Test")
    print("  Cardinal Element - Free API Enrichment Stack")
    print("=" * 60)

    # Initialize client (no API key for testing)
    # For production, pass api_key="your_key" to avoid 500/day limit
    client = CensusClient()

    try:
        await test_industry_benchmarks(client)
        await test_state_data(client)
        await test_zip_code_data(client)
        await test_market_size(client)
        await test_prospect_benchmark(client)
        await test_top_states(client)
        await test_naics_lookup(client)
        await test_icp_industries(client)

        print_section("All Tests Complete")
        print("\n  Census Bureau API integration is working correctly.")
        print("  Rate limit: 500 queries/day (unlimited with free API key)")
        print("  Cost: $0/month")
        print("\n  To get unlimited queries, sign up for free API key at:")
        print("  https://api.census.gov/data/key_signup.html")

    except Exception as e:
        print(f"\nError during testing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
