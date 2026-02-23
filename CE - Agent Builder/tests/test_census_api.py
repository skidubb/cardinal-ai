"""
Census Bureau API Integration Tests.

CTO Sprint 2 Deliverable 2: Integration Tests + CI Pipeline.

Tests verify that the Census Bureau API returns expected data structures
for industry benchmarking and prospect research. Real API calls.

Rate limit: 500 queries/day without key.
"""

import asyncio

import pytest

pytestmark = pytest.mark.integration

from csuite.tools.census_api import (
    CensusClient,
    IndustryBenchmarks,
    MarketSizeEstimate,
    ProspectBenchmark,
    StateBusinessData,
    ZipCodeData,
    ICP_NAICS_CODES,
)


@pytest.fixture
def client():
    """Create a fresh Census client (no API key)."""
    return CensusClient()


class TestIndustryBenchmarks:
    """Test national industry benchmark data."""

    def test_returns_benchmarks_for_valid_naics(self, client):
        """Should return benchmarks for Computer Systems Design."""
        benchmarks = asyncio.run(client.get_industry_benchmarks("541512"))

        assert benchmarks is not None
        assert isinstance(benchmarks, IndustryBenchmarks)
        assert benchmarks.naics_code == "541512"

    def test_benchmarks_have_positive_values(self, client):
        """Establishments, employees, and payroll should be positive."""
        benchmarks = asyncio.run(client.get_industry_benchmarks("541611"))

        assert benchmarks is not None
        assert benchmarks.establishments > 0
        assert benchmarks.total_employees > 0
        assert benchmarks.total_payroll > 0

    def test_avg_employees_calculated(self, client):
        """Average employees per firm should be calculated correctly."""
        benchmarks = asyncio.run(client.get_industry_benchmarks("541512"))

        assert benchmarks is not None
        assert benchmarks.avg_employees_per_firm > 0
        expected = benchmarks.total_employees / benchmarks.establishments
        assert abs(benchmarks.avg_employees_per_firm - expected) < 0.01


class TestStateData:
    """Test state-level business data."""

    def test_state_data_by_abbreviation(self, client):
        """Should accept state abbreviation (CA)."""
        data = asyncio.run(client.get_state_business_data("541512", "CA"))

        assert data is not None
        assert isinstance(data, StateBusinessData)
        assert data.establishments > 0

    def test_state_data_has_employees(self, client):
        """State data should include employee count."""
        data = asyncio.run(client.get_state_business_data("541611", "NY"))

        assert data is not None
        assert data.employees > 0


class TestZipCodeData:
    """Test ZIP code business data."""

    def test_zip_code_returns_data(self, client):
        """NYC ZIP should have consulting firms."""
        data = asyncio.run(client.get_zip_code_data("10001", "541611"))

        # May return None for some ZIP/NAICS combinations
        if data is not None:
            assert isinstance(data, ZipCodeData)
            assert data.establishments >= 0


class TestMarketSize:
    """Test market size estimation."""

    def test_national_market_size(self, client):
        """National market size should be estimable."""
        market = asyncio.run(client.estimate_market_size("541613"))

        assert market is not None
        assert isinstance(market, MarketSizeEstimate)
        assert market.total_establishments > 0
        assert market.estimated_revenue > 0

    def test_state_market_size(self, client):
        """State-level market size should work."""
        market = asyncio.run(client.estimate_market_size("541512", "CA"))

        if market is not None:
            assert market.geography == "CA"
            assert market.total_establishments > 0


class TestProspectBenchmark:
    """Test prospect benchmarking."""

    def test_benchmark_returns_result(self, client):
        """Benchmarking a prospect should return a result."""
        benchmark = asyncio.run(
            client.benchmark_prospect(75, "541512")
        )

        assert benchmark is not None
        assert isinstance(benchmark, ProspectBenchmark)
        assert benchmark.prospect_employees == 75

    def test_icp_fit_in_range(self, client):
        """Company with 75 employees should be ICP fit."""
        benchmark = asyncio.run(
            client.benchmark_prospect(75, "541512")
        )

        assert benchmark is not None
        assert benchmark.icp_fit is True

    def test_icp_fit_out_of_range(self, client):
        """Company with 5 employees should not be ICP fit."""
        benchmark = asyncio.run(
            client.benchmark_prospect(5, "541512")
        )

        assert benchmark is not None
        assert benchmark.icp_fit is False

    def test_signals_populated(self, client):
        """Benchmark should include signal explanations."""
        benchmark = asyncio.run(
            client.benchmark_prospect(75, "541611")
        )

        assert benchmark is not None
        assert len(benchmark.signals) > 0


class TestNAICSLookup:
    """Test NAICS code lookup."""

    def test_lookup_consulting(self, client):
        """Should find consulting-related NAICS codes."""
        matches = client.lookup_naics_code("consulting")
        assert len(matches) > 0
        for code, desc in matches:
            assert "consulting" in desc.lower() or "Consulting" in desc

    def test_icp_naics_codes_populated(self):
        """ICP NAICS codes should have entries."""
        assert len(ICP_NAICS_CODES) > 0
        assert "541512" in ICP_NAICS_CODES
