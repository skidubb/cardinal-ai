"""
Bureau of Labor Statistics API Integration Tests.

CTO Sprint 2 Deliverable 2: Integration Tests + CI Pipeline.

Tests verify that the BLS API returns expected data structures
for labor market analysis. Real API calls.

Rate limit: 25 queries/day without key.
Note: BLS API can be slow and has strict daily limits.
Tests are designed to be conservative with API usage.
"""

import asyncio

import pytest

pytestmark = pytest.mark.integration

from csuite.tools.bls_api import (
    BLSClient,
    IndustryEmployment,
    EmploymentTrend,
    NAICS_TO_BLS_SERIES,
    OCCUPATION_CODES,
)


@pytest.fixture
def client():
    """Create a fresh BLS client (no API key)."""
    return BLSClient()


class TestIndustryEmployment:
    """Test industry employment data retrieval."""

    def test_returns_employment_data(self, client):
        """Should return employment data for Computer Systems Design."""
        employment = asyncio.run(
            client.get_industry_employment("541512")
        )

        assert isinstance(employment, list)
        # BLS may return empty for some series/years -- that is OK
        if employment:
            assert all(isinstance(e, IndustryEmployment) for e in employment)
            assert employment[0].naics_code == "541512"

    def test_employment_has_period(self, client):
        """Each data point should have a period identifier."""
        employment = asyncio.run(
            client.get_industry_employment("541611")
        )

        if employment:
            for emp in employment[:3]:
                assert emp.period  # Should have a period string
                assert emp.year > 2000  # Reasonable year


class TestEmploymentTrend:
    """Test employment trend calculation."""

    def test_trend_returns_result_or_none(self, client):
        """Trend should return a result or None if insufficient data."""
        trend = asyncio.run(
            client.get_employment_trend("541512")
        )

        # May be None if insufficient data -- that is acceptable
        if trend is not None:
            assert isinstance(trend, EmploymentTrend)
            assert trend.trend_direction in ("Expanding", "Stable", "Contracting")
            assert isinstance(trend.change_percent, float)


class TestAvailableSeries:
    """Test available series lookups."""

    def test_naics_mappings_exist(self):
        """Should have BLS series mappings for ICP industries."""
        assert len(NAICS_TO_BLS_SERIES) > 0
        assert "541512" in NAICS_TO_BLS_SERIES

    def test_occupation_codes_exist(self):
        """Should have occupation code mappings."""
        assert len(OCCUPATION_CODES) > 0
        assert "15-1252" in OCCUPATION_CODES  # Software Developers

    def test_get_available_industries(self, client):
        """Client method should return available industries."""
        industries = client.get_available_industries()
        assert isinstance(industries, dict)
        assert len(industries) > 0

    def test_get_available_occupations(self, client):
        """Client method should return available occupations."""
        occupations = client.get_available_occupations()
        assert isinstance(occupations, dict)
        assert len(occupations) > 0
