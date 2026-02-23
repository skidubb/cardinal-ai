"""
SEC EDGAR API Integration for Prospect Research.

Free API for pulling financial filings, funding data, and company information
from SEC public records. Replaces paid services like BuiltWith Pro ($295/mo).

Endpoints:
- Company Search by CIK or Ticker
- Filing Retrieval (10-K, 10-Q, Form D, S-1, 13-F)
- XBRL Financial Data Extraction

Rate Limits: 10 requests/second, no daily limit.
Authentication: None required. User-Agent header mandatory.

Usage:
    from csuite.tools.sec_edgar import SECEdgarClient

    client = SECEdgarClient()

    # Get company financials by ticker
    financials = await client.get_company_financials("AAPL")

    # Search for Form D filings (private funding rounds)
    funding = await client.get_form_d_filings("Stripe")

    # Get company submissions history
    submissions = await client.get_company_submissions("320193")
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from csuite.tools.resilience import resilient

# SEC EDGAR requires a User-Agent header with contact info
DEFAULT_USER_AGENT = "Cardinal Element contact@cardinalelement.com"

# Rate limit: 10 requests/second
RATE_LIMIT_DELAY = 0.1  # 100ms between requests


@dataclass
class CompanyInfo:
    """Basic company information from SEC."""

    cik: str
    name: str
    ticker: str | None = None
    sic: str | None = None  # Standard Industrial Classification
    sic_description: str | None = None
    state: str | None = None
    fiscal_year_end: str | None = None
    entity_type: str | None = None


@dataclass
class Filing:
    """A single SEC filing."""

    accession_number: str
    form_type: str
    filing_date: str
    report_date: str | None = None
    primary_document: str | None = None
    description: str | None = None


@dataclass
class FinancialData:
    """Extracted financial metrics from XBRL data."""

    cik: str
    company_name: str
    revenue: float | None = None
    revenue_date: str | None = None
    net_income: float | None = None
    net_income_date: str | None = None
    total_assets: float | None = None
    total_assets_date: str | None = None
    employees: int | None = None
    employees_date: str | None = None
    fiscal_year: str | None = None
    currency: str = "USD"


@dataclass
class FormDFiling:
    """Form D filing (private placement / funding round)."""

    accession_number: str
    filing_date: str
    company_name: str
    offering_amount: float | None = None
    amount_sold: float | None = None
    remaining_amount: float | None = None
    investors_count: int | None = None
    is_amendment: bool = False


@dataclass
class ProspectResearchBrief:
    """Structured output for prospect research."""

    company_info: CompanyInfo | None = None
    financials: FinancialData | None = None
    recent_filings: list[Filing] = field(default_factory=list)
    form_d_filings: list[FormDFiling] = field(default_factory=list)
    icp_fit: dict[str, Any] = field(default_factory=dict)
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RateLimiter:
    """Simple rate limiter for SEC EDGAR's 10 req/sec limit."""

    def __init__(self, min_interval: float = RATE_LIMIT_DELAY):
        self.min_interval = min_interval
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait if necessary to respect rate limit."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self._last_request = time.monotonic()


class SECEdgarClient:
    """Client for SEC EDGAR API.

    Provides access to company filings, financial data, and funding information
    from SEC public records.
    """

    BASE_URL = "https://data.sec.gov"
    WWW_URL = "https://www.sec.gov"
    EFTS_URL = "https://efts.sec.gov"

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT):
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }
        self._rate_limiter = RateLimiter()
        self._ticker_to_cik: dict[str, str] = {}

    @resilient(api_name="sec_edgar", cache_ttl=300)
    async def _request(self, url: str, params: dict | None = None) -> dict[str, Any] | None:
        """Make a rate-limited request to SEC EDGAR."""
        await self._rate_limiter.acquire()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
            except httpx.RequestError as e:
                raise SECEdgarError(f"Request failed: {e}") from e

    async def _load_ticker_to_cik_mapping(self) -> None:
        """Load the SEC's ticker to CIK mapping file."""
        if self._ticker_to_cik:
            return  # Already loaded

        url = f"{self.WWW_URL}/files/company_tickers.json"
        data = await self._request(url)
        if data:
            for entry in data.values():
                ticker = entry.get("ticker", "").upper()
                cik = str(entry.get("cik_str", "")).zfill(10)
                if ticker and cik:
                    self._ticker_to_cik[ticker] = cik

    async def ticker_to_cik(self, ticker: str) -> str | None:
        """Convert a stock ticker to SEC CIK number."""
        await self._load_ticker_to_cik_mapping()
        return self._ticker_to_cik.get(ticker.upper())

    def _normalize_cik(self, cik: str) -> str:
        """Normalize CIK to 10-digit zero-padded format."""
        return cik.lstrip("0").zfill(10)

    async def get_company_submissions(self, cik: str) -> dict[str, Any] | None:
        """Get company submissions and filing history.

        Args:
            cik: SEC CIK number (with or without leading zeros)

        Returns:
            dict with company info and recent filings, or None if not found
        """
        normalized_cik = self._normalize_cik(cik)
        url = f"{self.BASE_URL}/submissions/CIK{normalized_cik}.json"
        return await self._request(url)

    async def get_company_facts(self, cik: str) -> dict[str, Any] | None:
        """Get XBRL company facts (structured financial data).

        Args:
            cik: SEC CIK number

        Returns:
            dict with XBRL financial data, or None if not found
        """
        normalized_cik = self._normalize_cik(cik)
        url = f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{normalized_cik}.json"
        return await self._request(url)

    async def get_company_info(self, cik_or_ticker: str) -> CompanyInfo | None:
        """Get basic company information.

        Args:
            cik_or_ticker: CIK number or stock ticker

        Returns:
            CompanyInfo dataclass or None if not found
        """
        # Try to resolve ticker to CIK
        if not cik_or_ticker.isdigit():
            cik = await self.ticker_to_cik(cik_or_ticker)
            if not cik:
                return None
        else:
            cik = cik_or_ticker

        data = await self.get_company_submissions(cik)
        if not data:
            return None

        return CompanyInfo(
            cik=self._normalize_cik(cik),
            name=data.get("name", ""),
            ticker=data.get("tickers", [None])[0] if data.get("tickers") else None,
            sic=data.get("sic"),
            sic_description=data.get("sicDescription"),
            state=data.get("stateOfIncorporation"),
            fiscal_year_end=data.get("fiscalYearEnd"),
            entity_type=data.get("entityType"),
        )

    async def get_company_financials(self, cik_or_ticker: str) -> FinancialData | None:
        """Get company financial data from XBRL filings.

        Extracts key metrics: revenue, net income, total assets, employee count.

        Args:
            cik_or_ticker: CIK number or stock ticker

        Returns:
            FinancialData dataclass or None if not found
        """
        # Resolve ticker to CIK
        if not cik_or_ticker.isdigit():
            cik = await self.ticker_to_cik(cik_or_ticker)
            if not cik:
                return None
        else:
            cik = cik_or_ticker

        data = await self.get_company_facts(cik)
        if not data:
            return None

        financials = FinancialData(
            cik=self._normalize_cik(cik),
            company_name=data.get("entityName", ""),
        )

        facts = data.get("facts", {})
        us_gaap = facts.get("us-gaap", {})

        # Extract revenue (try multiple field names)
        revenue_fields = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                         "SalesRevenueNet", "TotalRevenue"]
        for field_name in revenue_fields:
            if field_name in us_gaap:
                units = us_gaap[field_name].get("units", {})
                if "USD" in units:
                    values = units["USD"]
                    # Get most recent annual value (10-K)
                    annual_values = [v for v in values if v.get("form") == "10-K"]
                    if annual_values:
                        latest = max(annual_values, key=lambda x: x.get("end", ""))
                        financials.revenue = latest.get("val")
                        financials.revenue_date = latest.get("filed")
                        break

        # Extract net income
        net_income_fields = ["NetIncomeLoss", "ProfitLoss", "NetIncome"]
        for field_name in net_income_fields:
            if field_name in us_gaap:
                units = us_gaap[field_name].get("units", {})
                if "USD" in units:
                    values = units["USD"]
                    annual_values = [v for v in values if v.get("form") == "10-K"]
                    if annual_values:
                        latest = max(annual_values, key=lambda x: x.get("end", ""))
                        financials.net_income = latest.get("val")
                        financials.net_income_date = latest.get("filed")
                        break

        # Extract total assets
        if "Assets" in us_gaap:
            units = us_gaap["Assets"].get("units", {})
            if "USD" in units:
                values = units["USD"]
                annual_values = [v for v in values if v.get("form") == "10-K"]
                if annual_values:
                    latest = max(annual_values, key=lambda x: x.get("end", ""))
                    financials.total_assets = latest.get("val")
                    financials.total_assets_date = latest.get("filed")

        # Extract employee count
        dei = facts.get("dei", {})
        if "EntityCommonStockSharesOutstanding" in dei:
            pass  # Skip shares, look for employees

        # Try us-gaap for employee count
        employee_fields = ["EntityNumberOfEmployees", "NumberOfEmployees"]
        for field_name in employee_fields:
            if field_name in us_gaap:
                units = us_gaap[field_name].get("units", {})
                if "pure" in units:
                    values = units["pure"]
                    if values:
                        latest = max(values, key=lambda x: x.get("end", ""))
                        financials.employees = int(latest.get("val", 0))
                        financials.employees_date = latest.get("filed")
                        break

        return financials

    async def get_recent_filings(
        self,
        cik_or_ticker: str,
        form_types: list[str] | None = None,
        limit: int = 10
    ) -> list[Filing]:
        """Get recent SEC filings for a company.

        Args:
            cik_or_ticker: CIK number or stock ticker
            form_types: Filter by form types (e.g., ["10-K", "10-Q", "8-K"])
            limit: Maximum number of filings to return

        Returns:
            List of Filing dataclasses
        """
        # Resolve ticker to CIK
        if not cik_or_ticker.isdigit():
            cik = await self.ticker_to_cik(cik_or_ticker)
            if not cik:
                return []
        else:
            cik = cik_or_ticker

        data = await self.get_company_submissions(cik)
        if not data:
            return []

        filings = []
        recent = data.get("filings", {}).get("recent", {})

        if not recent:
            return []

        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        for i in range(min(len(accession_numbers), 100)):  # Cap at 100
            form_type = forms[i] if i < len(forms) else ""

            # Filter by form type if specified
            if form_types and form_type not in form_types:
                continue

            filings.append(Filing(
                accession_number=accession_numbers[i],
                form_type=form_type,
                filing_date=filing_dates[i] if i < len(filing_dates) else "",
                report_date=report_dates[i] if i < len(report_dates) else None,
                primary_document=primary_docs[i] if i < len(primary_docs) else None,
                description=descriptions[i] if i < len(descriptions) else None,
            ))

            if len(filings) >= limit:
                break

        return filings

    async def search_companies(self, query: str, limit: int = 10) -> list[CompanyInfo]:
        """Search for companies by name.

        Uses SEC's full-text search endpoint.

        Args:
            query: Company name to search for
            limit: Maximum number of results

        Returns:
            List of CompanyInfo dataclasses
        """
        # Use SEC's full-text search
        url = f"{self.EFTS_URL}/LATEST/search-index"
        params = {
            "q": query,
            "dateRange": "custom",
            "startdt": "2020-01-01",
            "enddt": datetime.now().strftime("%Y-%m-%d"),
            "forms": "10-K,10-Q",
        }

        data = await self._request(url, params)
        if not data or "hits" not in data:
            return []

        companies = []
        seen_ciks = set()

        for hit in data.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            cik = source.get("ciks", [""])[0]

            if cik and cik not in seen_ciks:
                seen_ciks.add(cik)
                companies.append(CompanyInfo(
                    cik=self._normalize_cik(cik),
                    name=source.get("display_names", [""])[0],
                    ticker=None,  # Would need separate lookup
                ))

                if len(companies) >= limit:
                    break

        return companies

    async def get_form_d_filings(self, company_name: str) -> list[FormDFiling]:
        """Search for Form D filings (private placements / funding rounds).

        Form D filings indicate private securities offerings, which can reveal:
        - Funding round amounts
        - Number of investors
        - Amendment history (follow-on rounds)

        Args:
            company_name: Company name to search for

        Returns:
            List of FormDFiling dataclasses
        """
        # Use SEC's full-text search for Form D
        url = f"{self.EFTS_URL}/LATEST/search-index"
        params = {
            "q": company_name,
            "dateRange": "custom",
            "startdt": "2015-01-01",
            "enddt": datetime.now().strftime("%Y-%m-%d"),
            "forms": "D,D/A",  # D and D amendments
        }

        data = await self._request(url, params)
        if not data or "hits" not in data:
            return []

        filings = []
        for hit in data.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})

            filings.append(FormDFiling(
                accession_number=source.get("adsh", ""),
                filing_date=source.get("file_date", ""),
                company_name=source.get("display_names", [""])[0],
                is_amendment="D/A" in source.get("form", ""),
            ))

        return filings

    async def generate_prospect_brief(self, cik_or_ticker: str) -> ProspectResearchBrief:
        """Generate a comprehensive prospect research brief.

        Aggregates company info, financials, filings, and ICP fit analysis
        into a single structured output suitable for prospect research.

        Args:
            cik_or_ticker: CIK number or stock ticker

        Returns:
            ProspectResearchBrief with all available data
        """
        brief = ProspectResearchBrief()

        # Fetch company info
        brief.company_info = await self.get_company_info(cik_or_ticker)
        if not brief.company_info:
            return brief

        # Fetch financials
        brief.financials = await self.get_company_financials(cik_or_ticker)

        # Fetch recent filings
        brief.recent_filings = await self.get_recent_filings(
            cik_or_ticker,
            form_types=["10-K", "10-Q", "8-K", "S-1"],
            limit=5
        )

        # Search for Form D filings by company name
        if brief.company_info.name:
            brief.form_d_filings = await self.get_form_d_filings(brief.company_info.name)

        # Calculate ICP fit (B2B operators, $5-40M ARR, 20-150 employees)
        brief.icp_fit = self._calculate_icp_fit(brief)

        return brief

    def _calculate_icp_fit(self, brief: ProspectResearchBrief) -> dict[str, Any]:
        """Calculate ICP fit score based on Cardinal Element criteria.

        ICP: B2B operators, $5-40M ARR, 20-150 employees (NOT B2B SaaS)

        Returns:
            dict with fit scores and reasoning
        """
        fit = {
            "overall_score": 0,
            "revenue_fit": "unknown",
            "employee_fit": "unknown",
            "industry_fit": "unknown",
            "signals": [],
            "disqualifiers": [],
        }

        if not brief.financials:
            fit["signals"].append("No financial data available - may be private company")
            return fit

        # Revenue check ($5-40M ARR)
        if brief.financials.revenue:
            revenue_m = brief.financials.revenue / 1_000_000
            if 5 <= revenue_m <= 40:
                fit["revenue_fit"] = "strong"
                fit["overall_score"] += 40
                fit["signals"].append(f"Revenue ${revenue_m:.1f}M in ICP range ($5-40M)")
            elif revenue_m < 5:
                fit["revenue_fit"] = "below"
                fit["overall_score"] += 10
                fit["signals"].append(f"Revenue ${revenue_m:.1f}M below ICP minimum ($5M)")
            else:
                fit["revenue_fit"] = "above"
                fit["overall_score"] += 20
                fit["signals"].append(f"Revenue ${revenue_m:.1f}M above ICP maximum ($40M)")

        # Employee check (20-150 employees)
        if brief.financials.employees:
            emp = brief.financials.employees
            if 20 <= emp <= 150:
                fit["employee_fit"] = "strong"
                fit["overall_score"] += 40
                fit["signals"].append(f"{emp} employees in ICP range (20-150)")
            elif emp < 20:
                fit["employee_fit"] = "below"
                fit["overall_score"] += 10
                fit["signals"].append(f"{emp} employees below ICP minimum (20)")
            else:
                fit["employee_fit"] = "above"
                fit["overall_score"] += 15
                fit["signals"].append(f"{emp} employees above ICP maximum (150)")

        # Industry check (B2B operators, NOT SaaS)
        if brief.company_info and brief.company_info.sic_description:
            sic_desc = brief.company_info.sic_description.lower()

            # SaaS indicators (disqualifier)
            saas_keywords = ["software", "computer programming", "data processing"]
            if any(kw in sic_desc for kw in saas_keywords):
                fit["industry_fit"] = "saas_disqualified"
                fit["disqualifiers"].append(
                    f"SIC indicates SaaS: {brief.company_info.sic_description}"
                )
            else:
                # B2B operators (target)
                b2b_keywords = ["consulting", "services", "engineering", "management",
                               "professional", "technical", "healthcare"]
                if any(kw in sic_desc for kw in b2b_keywords):
                    fit["industry_fit"] = "strong"
                    fit["overall_score"] += 20
                    fit["signals"].append(
                        f"B2B operator industry: {brief.company_info.sic_description}"
                    )

        return fit


class SECEdgarError(Exception):
    """Exception raised for SEC EDGAR API errors."""

    pass
