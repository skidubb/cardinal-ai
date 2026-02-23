"""
SEC EDGAR API Integration Tests.

CTO Sprint 2 Deliverable 2: Integration Tests + CI Pipeline.

Tests verify that the SEC EDGAR API returns expected data structures
and that the client handles edge cases gracefully. These tests make
real API calls -- they are designed to catch breaking changes in the
SEC EDGAR API before prospects see broken demos.

Rate limit: 10 req/sec (respected by client's RateLimiter).
"""

import asyncio

import pytest

from csuite.tools.sec_edgar import (
    CompanyInfo,
    FinancialData,
    Filing,
    ProspectResearchBrief,
    SECEdgarClient,
)


@pytest.fixture
def client():
    """Create a fresh SEC EDGAR client."""
    return SECEdgarClient()


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestTickerLookup:
    """Test ticker to CIK conversion."""

    def test_valid_ticker_returns_cik(self, client):
        """AAPL should resolve to a valid CIK."""
        cik = asyncio.run(client.ticker_to_cik("AAPL"))
        assert cik is not None
        assert len(cik) == 10  # CIK is zero-padded to 10 digits
        assert cik.isdigit()

    def test_invalid_ticker_returns_none(self, client):
        """Invalid ticker should return None, not raise."""
        cik = asyncio.run(client.ticker_to_cik("ZZZZZZINVALID"))
        assert cik is None

    def test_case_insensitive(self, client):
        """Ticker lookup should be case-insensitive."""
        upper = asyncio.run(client.ticker_to_cik("AAPL"))
        lower = asyncio.run(client.ticker_to_cik("aapl"))
        assert upper == lower


class TestCompanyInfo:
    """Test company info retrieval."""

    def test_valid_ticker_returns_company_info(self, client):
        """AAPL should return a populated CompanyInfo."""
        info = asyncio.run(client.get_company_info("AAPL"))

        assert info is not None
        assert isinstance(info, CompanyInfo)
        assert info.name  # Should have a name
        assert info.cik  # Should have a CIK
        assert info.ticker  # Should have a ticker

    def test_company_info_has_sic(self, client):
        """Company info should include SIC classification."""
        info = asyncio.run(client.get_company_info("MSFT"))

        assert info is not None
        assert info.sic is not None or info.sic_description is not None

    def test_invalid_ticker_returns_none(self, client):
        """Invalid ticker should return None."""
        info = asyncio.run(client.get_company_info("ZZZZZZINVALID"))
        assert info is None


class TestFinancialData:
    """Test financial data extraction."""

    def test_valid_company_returns_financials(self, client):
        """MSFT should have financial data (large company with XBRL filings)."""
        financials = asyncio.run(client.get_company_financials("MSFT"))

        assert financials is not None
        assert isinstance(financials, FinancialData)
        assert financials.company_name  # Should have company name

    def test_revenue_is_positive(self, client):
        """Revenue for a major company should be positive."""
        financials = asyncio.run(client.get_company_financials("AAPL"))

        assert financials is not None
        assert financials.revenue is not None
        assert financials.revenue > 0

    def test_financials_contain_expected_fields(self, client):
        """Financial data should have at least revenue and company name."""
        financials = asyncio.run(client.get_company_financials("GOOGL"))

        assert financials is not None
        assert financials.cik  # CIK populated
        assert financials.company_name  # Name populated
        # Revenue may or may not be present depending on XBRL availability
        # but company_name and cik should always be there


class TestRecentFilings:
    """Test recent filings retrieval."""

    def test_returns_filings_list(self, client):
        """Should return a list of Filing objects."""
        filings = asyncio.run(client.get_recent_filings("TSLA", limit=5))

        assert isinstance(filings, list)
        assert len(filings) > 0
        assert all(isinstance(f, Filing) for f in filings)

    def test_filings_have_required_fields(self, client):
        """Each filing should have form type and date."""
        filings = asyncio.run(client.get_recent_filings("AAPL", limit=3))

        for filing in filings:
            assert filing.form_type  # Must have form type
            assert filing.filing_date  # Must have filing date

    def test_form_type_filter(self, client):
        """Filtering by form type should only return matching forms."""
        filings = asyncio.run(
            client.get_recent_filings("MSFT", form_types=["10-K"], limit=3)
        )

        for filing in filings:
            assert filing.form_type == "10-K"


class TestCompanySearch:
    """Test company search functionality."""

    def test_search_returns_results(self, client):
        """Searching for 'consulting' should return companies."""
        companies = asyncio.run(client.search_companies("consulting", limit=5))

        assert isinstance(companies, list)
        assert len(companies) > 0
        assert all(isinstance(c, CompanyInfo) for c in companies)

    def test_search_results_have_cik(self, client):
        """Each search result should have a CIK."""
        companies = asyncio.run(client.search_companies("engineering", limit=3))

        for company in companies:
            assert company.cik
            assert company.name


class TestProspectBrief:
    """Test full prospect research brief generation."""

    def test_brief_has_company_info(self, client):
        """Brief should include company info for a valid ticker."""
        brief = asyncio.run(client.generate_prospect_brief("CRM"))

        assert isinstance(brief, ProspectResearchBrief)
        assert brief.company_info is not None
        assert brief.company_info.name

    def test_brief_has_icp_fit(self, client):
        """Brief should include ICP fit scoring."""
        brief = asyncio.run(client.generate_prospect_brief("EPAM"))

        assert brief.icp_fit is not None
        assert "overall_score" in brief.icp_fit
        assert isinstance(brief.icp_fit["overall_score"], (int, float))


class TestICPScoring:
    """Test ICP fit scoring logic."""

    def test_icp_score_has_required_keys(self, client):
        """ICP fit dict should have expected keys."""
        brief = ProspectResearchBrief(
            company_info=CompanyInfo(cik="0000000001", name="Test Corp"),
            financials=FinancialData(
                cik="0000000001",
                company_name="Test Corp",
                revenue=20_000_000,
                employees=75,
            ),
        )
        fit = client._calculate_icp_fit(brief)

        assert "overall_score" in fit
        assert "revenue_fit" in fit
        assert "employee_fit" in fit
        assert "signals" in fit

    def test_in_range_company_scores_high(self, client):
        """Company in ICP range should score well."""
        brief = ProspectResearchBrief(
            company_info=CompanyInfo(
                cik="0000000001",
                name="Perfect ICP Corp",
                sic_description="Management consulting services",
            ),
            financials=FinancialData(
                cik="0000000001",
                company_name="Perfect ICP Corp",
                revenue=20_000_000,
                employees=75,
            ),
        )
        fit = client._calculate_icp_fit(brief)

        assert fit["overall_score"] >= 80  # Revenue (40) + Employees (40) + Industry (20)
        assert fit["revenue_fit"] == "strong"
        assert fit["employee_fit"] == "strong"
