"""
Bureau of Labor Statistics (BLS) API Integration for Prospect Research.

Free API for industry wages, employment trends, and labor market data.
Used to assess industry health and benchmark labor costs.

Endpoints:
- QCEW (Quarterly Census of Employment and Wages) — Industry employment & wages
- OES (Occupational Employment Statistics) — Occupation-level data
- CPI (Consumer Price Index) — Inflation adjustments

Rate Limits: 25 queries/day without key. 500 queries/day with free API key.
Authentication: Optional API key (free signup at bls.gov).

Usage:
    from csuite.tools.bls_api import BLSClient

    client = BLSClient()  # Or BLSClient(api_key="your_key")

    # Get industry employment data
    employment = await client.get_industry_employment("541512")  # Computer Systems Design

    # Get wage data for an occupation
    wages = await client.get_occupation_wages("15-1252")  # Software Developers

    # Calculate employment trend
    trend = await client.get_employment_trend("541512")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from csuite.tools.resilience import resilient

# BLS Series ID prefixes
# QCEW: ENU{state}{area}{ownership}{size}{naics}
# CEU: Current Employment Statistics
# OES: Occupational Employment Statistics

# Common NAICS to BLS series mappings for ICP industries
NAICS_TO_BLS_SERIES = {
    "541512": "CEU6054151201",  # Computer Systems Design
    "541611": "CEU6054161101",  # Management Consulting
    "541613": "CEU6054161301",  # Marketing Consulting
    "541330": "CEU6054133001",  # Engineering Services
    "541110": "CEU6054111001",  # Legal Services
    "541211": "CEU6054121101",  # Accounting Services
    "621111": "CEU6562111101",  # Physicians Offices
    "523110": "CEU5552311001",  # Investment Banking
}

# Common occupation codes (SOC)
OCCUPATION_CODES = {
    "15-1252": "Software Developers",
    "15-1211": "Computer Systems Analysts",
    "13-1111": "Management Analysts",
    "13-1161": "Market Research Analysts",
    "11-1021": "General and Operations Managers",
    "11-2021": "Marketing Managers",
    "11-3031": "Financial Managers",
    "15-2051": "Data Scientists",
    "13-2011": "Accountants and Auditors",
    "23-1011": "Lawyers",
}


@dataclass
class IndustryEmployment:
    """Industry employment data from BLS."""

    naics_code: str
    industry_name: str
    employment: int
    period: str  # e.g., "M12 2025"
    year: int
    series_id: str


@dataclass
class EmploymentTrend:
    """Employment trend analysis."""

    naics_code: str
    industry_name: str
    current_employment: int
    prior_employment: int
    change_absolute: int
    change_percent: float
    trend_direction: str  # "Expanding", "Stable", "Contracting"
    periods_analyzed: int
    start_period: str
    end_period: str


@dataclass
class OccupationWages:
    """Occupation wage data from OES."""

    occupation_code: str
    occupation_title: str
    employment: int | None
    mean_wage: float | None
    median_wage: float | None
    wage_10th_pct: float | None
    wage_90th_pct: float | None
    year: int


@dataclass
class IndustryWages:
    """Industry-level wage data."""

    naics_code: str
    industry_name: str
    avg_weekly_wage: float
    avg_annual_wage: float
    total_wages: float  # In thousands
    employment: int
    year: int
    quarter: str


@dataclass
class CPIData:
    """Consumer Price Index data."""

    period: str
    year: int
    value: float
    percent_change_from_year_ago: float | None = None


@dataclass
class LaborMarketAssessment:
    """Labor market assessment for prospect research."""

    naics_code: str
    industry_name: str
    employment_trend: str
    wage_level: str  # "High", "Medium", "Low"
    market_tightness: str  # "Tight", "Balanced", "Loose"
    signals: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)


class BLSClient:
    """Client for Bureau of Labor Statistics API.

    Provides access to employment, wage, and labor market data
    for prospect research and industry analysis.
    """

    BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def __init__(self, api_key: str | None = None):
        """Initialize BLS client.

        Args:
            api_key: Optional BLS API key. Without key, limited to 25 queries/day.
                    Get free key at: https://data.bls.gov/registrationEngine/
        """
        self.api_key = api_key
        self._request_count = 0
        self._last_reset = datetime.now()

    def _check_rate_limit(self) -> None:
        """Check if we're within rate limits."""
        now = datetime.now()
        if now.date() > self._last_reset.date():
            self._request_count = 0
            self._last_reset = now

        limit = 500 if self.api_key else 25
        if self._request_count >= limit:
            raise BLSAPIError(f"Daily rate limit exceeded ({limit} queries). "
                            "Get a free API key at https://data.bls.gov/registrationEngine/")

        self._request_count += 1

    @resilient(api_name="bls", cache_ttl=600)
    async def _request(
        self,
        series_ids: list[str],
        start_year: int,
        end_year: int,
        catalog: bool = False
    ) -> dict[str, Any]:
        """Make a request to the BLS API.

        Args:
            series_ids: List of BLS series IDs to fetch
            start_year: Start year for data
            end_year: End year for data
            catalog: Include series catalog info

        Returns:
            API response data
        """
        self._check_rate_limit()

        payload = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
            "catalog": catalog,
        }

        if self.api_key:
            payload["registrationkey"] = self.api_key

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "REQUEST_SUCCEEDED":
                    msg = data.get("message", ["Unknown error"])
                    raise BLSAPIError(f"BLS API error: {msg}")

                return data

            except httpx.HTTPStatusError as e:
                raise BLSAPIError(f"HTTP error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise BLSAPIError(f"Request failed: {e}")

    def _get_industry_name(self, naics_code: str) -> str:
        """Get industry name for NAICS code."""
        names = {
            "541512": "Computer Systems Design Services",
            "541611": "Management Consulting Services",
            "541613": "Marketing Consulting Services",
            "541330": "Engineering Services",
            "541110": "Legal Services",
            "541211": "Accounting Services",
            "621111": "Offices of Physicians",
            "523110": "Investment Banking",
            "541810": "Advertising Agencies",
            "561110": "Office Administrative Services",
        }
        return names.get(naics_code, f"Industry {naics_code}")

    async def get_industry_employment(
        self,
        naics_code: str,
        start_year: int | None = None,
        end_year: int | None = None
    ) -> list[IndustryEmployment]:
        """Get industry employment time series.

        Args:
            naics_code: 6-digit NAICS code
            start_year: Start year (default: 2 years ago)
            end_year: End year (default: current year)

        Returns:
            List of IndustryEmployment data points
        """
        current_year = datetime.now().year
        start_year = start_year or (current_year - 2)
        end_year = end_year or current_year

        # Get series ID for this NAICS
        series_id = NAICS_TO_BLS_SERIES.get(naics_code)
        if not series_id:
            # Try constructing a CES series ID
            series_id = f"CES{naics_code}01"

        data = await self._request([series_id], start_year, end_year)

        results = []
        for series in data.get("Results", {}).get("series", []):
            for point in series.get("data", []):
                try:
                    results.append(IndustryEmployment(
                        naics_code=naics_code,
                        industry_name=self._get_industry_name(naics_code),
                        employment=int(float(point.get("value", 0)) * 1000),  # In thousands
                        period=f"{point.get('period', '')} {point.get('year', '')}",
                        year=int(point.get("year", 0)),
                        series_id=series_id,
                    ))
                except (ValueError, TypeError):
                    continue

        return results

    async def get_employment_trend(
        self,
        naics_code: str,
        months: int = 12
    ) -> EmploymentTrend | None:
        """Calculate employment trend for an industry.

        Compares recent period to prior period to determine
        if industry is expanding, stable, or contracting.

        Args:
            naics_code: 6-digit NAICS code
            months: Number of months to analyze (default: 12)

        Returns:
            EmploymentTrend analysis or None if insufficient data
        """
        current_year = datetime.now().year
        employment_data = await self.get_industry_employment(
            naics_code,
            start_year=current_year - 3,
            end_year=current_year
        )

        if len(employment_data) < months * 2:
            return None

        # Sort by period (most recent first)
        sorted_data = sorted(
            employment_data,
            key=lambda x: (x.year, x.period),
            reverse=True
        )

        # Get recent and prior periods
        recent = sorted_data[:months]
        prior = sorted_data[months:months * 2]

        if not recent or not prior:
            return None

        recent_avg = sum(d.employment for d in recent) / len(recent)
        prior_avg = sum(d.employment for d in prior) / len(prior)

        if prior_avg == 0:
            return None

        change_pct = ((recent_avg - prior_avg) / prior_avg) * 100

        # Determine trend direction
        if change_pct > 2:
            direction = "Expanding"
        elif change_pct < -2:
            direction = "Contracting"
        else:
            direction = "Stable"

        return EmploymentTrend(
            naics_code=naics_code,
            industry_name=self._get_industry_name(naics_code),
            current_employment=int(recent_avg),
            prior_employment=int(prior_avg),
            change_absolute=int(recent_avg - prior_avg),
            change_percent=change_pct,
            trend_direction=direction,
            periods_analyzed=months,
            start_period=prior[-1].period if prior else "",
            end_period=recent[0].period if recent else "",
        )

    async def get_occupation_wages(
        self,
        occupation_code: str,
        year: int | None = None
    ) -> OccupationWages | None:
        """Get wage data for a specific occupation.

        Args:
            occupation_code: SOC occupation code (e.g., "15-1252")
            year: Data year (default: most recent)

        Returns:
            OccupationWages data or None if not found
        """
        year = year or datetime.now().year - 1  # OES data typically lagged

        # OES series format: OEUS{area}{industry}{occupation}{datatype}
        # National data uses area 000000, all industries 000000
        # Data types: 01=employment, 04=mean wage, 13=median wage
        base_id = f"OEUS00000000000000{occupation_code.replace('-', '')}"

        series_ids = [
            f"{base_id}01",  # Employment
            f"{base_id}04",  # Mean wage
            f"{base_id}13",  # Median wage
        ]

        try:
            data = await self._request(series_ids, year, year)
        except BLSAPIError:
            return None

        results = data.get("Results", {}).get("series", [])
        if not results:
            return None

        employment = None
        mean_wage = None
        median_wage = None

        for series in results:
            series_id = series.get("seriesID", "")
            values = series.get("data", [])
            if values:
                value = float(values[0].get("value", 0))
                if series_id.endswith("01"):
                    employment = int(value)
                elif series_id.endswith("04"):
                    mean_wage = value
                elif series_id.endswith("13"):
                    median_wage = value

        return OccupationWages(
            occupation_code=occupation_code,
            occupation_title=OCCUPATION_CODES.get(occupation_code, occupation_code),
            employment=employment,
            mean_wage=mean_wage,
            median_wage=median_wage,
            wage_10th_pct=None,
            wage_90th_pct=None,
            year=year,
        )

    async def get_cpi_data(
        self,
        start_year: int | None = None,
        end_year: int | None = None
    ) -> list[CPIData]:
        """Get Consumer Price Index data for inflation adjustments.

        Args:
            start_year: Start year
            end_year: End year

        Returns:
            List of CPIData points
        """
        current_year = datetime.now().year
        start_year = start_year or (current_year - 2)
        end_year = end_year or current_year

        # CPI-U All Items: CUUR0000SA0
        series_id = "CUUR0000SA0"

        data = await self._request([series_id], start_year, end_year)

        results = []
        for series in data.get("Results", {}).get("series", []):
            for point in series.get("data", []):
                try:
                    results.append(CPIData(
                        period=point.get("period", ""),
                        year=int(point.get("year", 0)),
                        value=float(point.get("value", 0)),
                    ))
                except (ValueError, TypeError):
                    continue

        # Calculate year-over-year changes
        if len(results) >= 12:
            for i, cpi in enumerate(results):
                # Find same month from previous year
                for j in range(i + 1, len(results)):
                    if (results[j].period == cpi.period and
                        results[j].year == cpi.year - 1):
                        cpi.percent_change_from_year_ago = (
                            (cpi.value - results[j].value) / results[j].value * 100
                        )
                        break

        return results

    async def assess_labor_market(
        self,
        naics_code: str
    ) -> LaborMarketAssessment | None:
        """Generate a labor market assessment for prospect research.

        Combines employment trend, wage data, and market indicators
        to assess industry labor market conditions.

        Args:
            naics_code: 6-digit NAICS code

        Returns:
            LaborMarketAssessment with signals and opportunities
        """
        trend = await self.get_employment_trend(naics_code)
        if not trend:
            return None

        signals = []
        opportunities = []

        # Assess employment trend
        if trend.trend_direction == "Expanding":
            signals.append(
                f"Industry employment growing {trend.change_percent:.1f}% year-over-year"
            )
            opportunities.append("Growing industry = budget for growth initiatives")
        elif trend.trend_direction == "Contracting":
            signals.append(
                f"Industry employment declining {abs(trend.change_percent):.1f}%"
                " year-over-year"
            )
            opportunities.append("Contracting industry = need for efficiency/automation")
        else:
            signals.append("Industry employment stable")

        # Wage level assessment (simplified)
        # High-wage industries typically have more consulting budget
        high_wage_industries = ["541512", "523110", "541110", "541211"]
        if naics_code in high_wage_industries:
            wage_level = "High"
            signals.append("High-wage industry (above average labor costs)")
            opportunities.append("High wages = budget for consulting services")
        else:
            wage_level = "Medium"
            signals.append("Medium-wage industry")

        # Market tightness (simplified heuristic)
        if trend.trend_direction == "Expanding" and trend.change_percent > 5:
            market_tightness = "Tight"
            signals.append("Tight labor market (high competition for talent)")
            opportunities.append("Talent shortages = pain point for automation/AI")
        elif trend.trend_direction == "Contracting":
            market_tightness = "Loose"
            signals.append("Loose labor market")
        else:
            market_tightness = "Balanced"
            signals.append("Balanced labor market")

        return LaborMarketAssessment(
            naics_code=naics_code,
            industry_name=self._get_industry_name(naics_code),
            employment_trend=trend.trend_direction,
            wage_level=wage_level,
            market_tightness=market_tightness,
            signals=signals,
            opportunities=opportunities,
        )

    def get_available_occupations(self) -> dict[str, str]:
        """Get list of available occupation codes and titles.

        Returns:
            Dict mapping occupation code to title
        """
        return OCCUPATION_CODES.copy()

    def get_available_industries(self) -> dict[str, str]:
        """Get list of industries with known BLS series mappings.

        Returns:
            Dict mapping NAICS code to series ID
        """
        return NAICS_TO_BLS_SERIES.copy()


class BLSAPIError(Exception):
    """Exception raised for BLS API errors."""

    pass
