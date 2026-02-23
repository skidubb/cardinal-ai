"""
Census Bureau API Integration for Prospect Research.

Free API for business counts, employment data, and industry benchmarks.
Used to validate prospect size and benchmark against industry averages.

Endpoints:
- County Business Patterns (CBP) — Business counts by industry
- Annual Business Survey (ABS) — Detailed business statistics
- ZIP Code Business Patterns (ZBP) — Local market data

Rate Limits: 500 queries/day without API key. Unlimited with free key.
Authentication: Optional API key (free signup at api.census.gov).

Usage:
    from csuite.tools.census_api import CensusClient

    client = CensusClient()  # Or CensusClient(api_key="your_key")

    # Get industry benchmarks
    benchmarks = await client.get_industry_benchmarks("541512")  # Computer Systems Design

    # Get state-level data
    state_data = await client.get_state_business_data("541512", state="06")  # California

    # Get ZIP code data
    zip_data = await client.get_zip_code_data("10001", "541512")  # NYC zip
"""

from dataclasses import dataclass, field
from datetime import datetime

import httpx

from csuite.tools.resilience import resilient

# NAICS codes for B2B operators (Cardinal Element ICP)
ICP_NAICS_CODES = {
    "541512": "Computer Systems Design Services",
    "541611": "Administrative Management Consulting",
    "541613": "Marketing Consulting Services",
    "541330": "Engineering Services",
    "541219": "Other Accounting Services",
    "541110": "Offices of Lawyers",
    "541211": "Offices of CPAs",
    "523110": "Investment Banking and Securities Dealing",
    "621111": "Offices of Physicians",
    "621210": "Offices of Dentists",
    "531210": "Offices of Real Estate Agents",
    "541810": "Advertising Agencies",
    "541820": "Public Relations Agencies",
    "541860": "Direct Mail Advertising",
    "541890": "Other Services Related to Advertising",
    "561110": "Office Administrative Services",
    "561320": "Temporary Help Services",
    "561612": "Security Guards and Patrol Services",
}

# State FIPS codes for common states
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
    "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
    "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
    "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
    "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
    "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
    "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
    "DC": "11", "PR": "72",
}


@dataclass
class IndustryBenchmarks:
    """Industry benchmark data from Census Bureau."""

    naics_code: str
    naics_description: str
    establishments: int
    total_employees: int
    total_payroll: int  # In thousands of dollars
    avg_employees_per_firm: float
    avg_payroll_per_employee: float  # In dollars
    year: int = 2021
    geography: str = "US"


@dataclass
class StateBusinessData:
    """Business data for a specific state."""

    state_fips: str
    state_name: str
    naics_code: str
    establishments: int
    employees: int
    payroll: int  # In thousands
    year: int = 2021


@dataclass
class ZipCodeData:
    """Business data for a specific ZIP code."""

    zip_code: str
    naics_code: str
    establishments: int
    employees: int | None = None  # Sometimes suppressed for privacy
    year: int = 2021


@dataclass
class MarketSizeEstimate:
    """Market size estimate for an industry in a geography."""

    naics_code: str
    naics_description: str
    geography: str
    total_establishments: int
    total_employees: int
    total_payroll: int
    estimated_revenue: float | None = None  # Estimated from payroll multiplier
    market_concentration: str = "unknown"  # High/Medium/Low
    icp_fit_industries: list[str] = field(default_factory=list)


@dataclass
class ProspectBenchmark:
    """Benchmark a prospect against industry averages."""

    prospect_employees: int
    prospect_revenue: float | None
    industry_avg_employees: float
    industry_avg_payroll_per_employee: float
    size_percentile: str  # "small", "medium", "large" relative to industry
    icp_fit: bool  # True if 20-150 employees
    signals: list[str] = field(default_factory=list)


class CensusClient:
    """Client for Census Bureau API.

    Provides access to business statistics for prospect research and
    industry benchmarking.
    """

    BASE_URL = "https://api.census.gov/data"
    LATEST_CBP_YEAR = 2021  # County Business Patterns
    LATEST_ZBP_YEAR = 2021  # ZIP Code Business Patterns

    def __init__(self, api_key: str | None = None):
        """Initialize Census client.

        Args:
            api_key: Optional Census API key. Without key, limited to 500 queries/day.
                    Get free key at: https://api.census.gov/data/key_signup.html
        """
        self.api_key = api_key
        self._request_count = 0
        self._last_reset = datetime.now()

    def _check_rate_limit(self) -> None:
        """Check if we're within rate limits (500/day without key)."""
        if self.api_key:
            return  # Unlimited with key

        # Reset counter if new day
        now = datetime.now()
        if now.date() > self._last_reset.date():
            self._request_count = 0
            self._last_reset = now

        if self._request_count >= 500:
            raise CensusAPIError("Daily rate limit exceeded (500 queries). Get a free API key.")

        self._request_count += 1

    @resilient(api_name="census", cache_ttl=600)
    async def _request(self, endpoint: str, params: dict[str, str]) -> list[list[str]]:
        """Make a request to the Census API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            List of rows (first row is headers)
        """
        self._check_rate_limit()

        if self.api_key:
            params["key"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 204:
                    return []  # No data
                if e.response.status_code == 400:
                    raise CensusAPIError(f"Invalid request: {e.response.text}")
                raise CensusAPIError(f"API error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise CensusAPIError(f"Request failed: {e}")

    def _get_naics_description(self, code: str) -> str:
        """Get NAICS description for a code."""
        return ICP_NAICS_CODES.get(code, f"Industry {code}")

    def _get_state_name(self, fips: str) -> str:
        """Get state name from FIPS code."""
        fips_to_name = {v: k for k, v in STATE_FIPS.items()}
        return fips_to_name.get(fips, fips)

    async def get_industry_benchmarks(
        self,
        naics_code: str,
        year: int | None = None
    ) -> IndustryBenchmarks | None:
        """Get national industry benchmarks.

        Args:
            naics_code: 6-digit NAICS industry code
            year: Data year (default: latest available)

        Returns:
            IndustryBenchmarks dataclass or None if no data
        """
        year = year or self.LATEST_CBP_YEAR

        params = {
            "get": "ESTAB,EMP,PAYANN",
            "for": "us:*",
            "NAICS2017": naics_code,
        }

        data = await self._request(f"{year}/cbp", params)

        if not data or len(data) < 2:
            return None

        # Parse response: [headers, data_row]
        headers = data[0]
        values = data[1]

        # Create index map
        idx = {h: i for i, h in enumerate(headers)}

        try:
            establishments = int(values[idx["ESTAB"]])
            employees = int(values[idx["EMP"]])
            payroll = int(values[idx["PAYANN"]])  # In thousands

            if establishments == 0:
                return None

            return IndustryBenchmarks(
                naics_code=naics_code,
                naics_description=self._get_naics_description(naics_code),
                establishments=establishments,
                total_employees=employees,
                total_payroll=payroll,
                avg_employees_per_firm=employees / establishments,
                avg_payroll_per_employee=(payroll * 1000) / employees if employees > 0 else 0,
                year=year,
                geography="US",
            )
        except (KeyError, ValueError, ZeroDivisionError):
            return None

    async def get_state_business_data(
        self,
        naics_code: str,
        state: str,
        year: int | None = None
    ) -> StateBusinessData | None:
        """Get business data for a specific state.

        Args:
            naics_code: 6-digit NAICS industry code
            state: State abbreviation (e.g., "CA") or FIPS code (e.g., "06")
            year: Data year (default: latest)

        Returns:
            StateBusinessData dataclass or None if no data
        """
        year = year or self.LATEST_CBP_YEAR

        # Convert state abbrev to FIPS if needed
        if len(state) == 2 and state.upper() in STATE_FIPS:
            state_fips = STATE_FIPS[state.upper()]
        else:
            state_fips = state

        params = {
            "get": "ESTAB,EMP,PAYANN",
            "for": f"state:{state_fips}",
            "NAICS2017": naics_code,
        }

        data = await self._request(f"{year}/cbp", params)

        if not data or len(data) < 2:
            return None

        headers = data[0]
        values = data[1]
        idx = {h: i for i, h in enumerate(headers)}

        try:
            return StateBusinessData(
                state_fips=state_fips,
                state_name=self._get_state_name(state_fips),
                naics_code=naics_code,
                establishments=int(values[idx["ESTAB"]]),
                employees=int(values[idx["EMP"]]),
                payroll=int(values[idx["PAYANN"]]),
                year=year,
            )
        except (KeyError, ValueError):
            return None

    async def get_all_states_data(
        self,
        naics_code: str,
        year: int | None = None
    ) -> list[StateBusinessData]:
        """Get business data for all states in an industry.

        Args:
            naics_code: 6-digit NAICS industry code
            year: Data year

        Returns:
            List of StateBusinessData for each state
        """
        year = year or self.LATEST_CBP_YEAR

        params = {
            "get": "ESTAB,EMP,PAYANN",
            "for": "state:*",
            "NAICS2017": naics_code,
        }

        data = await self._request(f"{year}/cbp", params)

        if not data or len(data) < 2:
            return []

        headers = data[0]
        idx = {h: i for i, h in enumerate(headers)}
        results = []

        for row in data[1:]:
            try:
                state_fips = row[idx["state"]]
                results.append(StateBusinessData(
                    state_fips=state_fips,
                    state_name=self._get_state_name(state_fips),
                    naics_code=naics_code,
                    establishments=int(row[idx["ESTAB"]]),
                    employees=int(row[idx["EMP"]]),
                    payroll=int(row[idx["PAYANN"]]),
                    year=year,
                ))
            except (KeyError, ValueError):
                continue

        return sorted(results, key=lambda x: x.establishments, reverse=True)

    async def get_zip_code_data(
        self,
        zip_code: str,
        naics_code: str,
        year: int | None = None
    ) -> ZipCodeData | None:
        """Get business data for a specific ZIP code.

        Args:
            zip_code: 5-digit ZIP code
            naics_code: 6-digit NAICS industry code
            year: Data year

        Returns:
            ZipCodeData dataclass or None if no data
        """
        year = year or self.LATEST_ZBP_YEAR

        params = {
            "get": "ESTAB,EMP",
            "for": f"zipcode:{zip_code}",
            "NAICS2017": naics_code,
        }

        data = await self._request(f"{year}/zbp", params)

        if not data or len(data) < 2:
            return None

        headers = data[0]
        values = data[1]
        idx = {h: i for i, h in enumerate(headers)}

        try:
            emp_val = values[idx.get("EMP", -1)] if "EMP" in idx else None
            return ZipCodeData(
                zip_code=zip_code,
                naics_code=naics_code,
                establishments=int(values[idx["ESTAB"]]),
                employees=int(emp_val) if emp_val and emp_val != "N" else None,
                year=year,
            )
        except (KeyError, ValueError):
            return None

    async def estimate_market_size(
        self,
        naics_code: str,
        state: str | None = None
    ) -> MarketSizeEstimate | None:
        """Estimate total market size for an industry.

        Uses payroll data with industry-specific revenue multipliers
        to estimate total addressable market.

        Args:
            naics_code: 6-digit NAICS industry code
            state: Optional state to limit geography

        Returns:
            MarketSizeEstimate dataclass
        """
        if state:
            data = await self.get_state_business_data(naics_code, state)
            if not data:
                return None
            geography = data.state_name
            establishments = data.establishments
            employees = data.employees
            payroll = data.payroll
        else:
            data = await self.get_industry_benchmarks(naics_code)
            if not data:
                return None
            geography = "US"
            establishments = data.establishments
            employees = data.total_employees
            payroll = data.total_payroll

        # Revenue multiplier: services typically 2-3x payroll
        # Conservative estimate at 2.5x
        estimated_revenue = payroll * 1000 * 2.5

        # Market concentration
        if establishments < 1000:
            concentration = "High"
        elif establishments < 10000:
            concentration = "Medium"
        else:
            concentration = "Low"

        return MarketSizeEstimate(
            naics_code=naics_code,
            naics_description=self._get_naics_description(naics_code),
            geography=geography,
            total_establishments=establishments,
            total_employees=employees,
            total_payroll=payroll,
            estimated_revenue=estimated_revenue,
            market_concentration=concentration,
            icp_fit_industries=list(ICP_NAICS_CODES.keys()),
        )

    async def benchmark_prospect(
        self,
        prospect_employees: int,
        naics_code: str,
        prospect_revenue: float | None = None
    ) -> ProspectBenchmark | None:
        """Benchmark a prospect against industry averages.

        Useful for ICP validation and prospect scoring.

        Args:
            prospect_employees: Number of employees at prospect company
            naics_code: Prospect's NAICS industry code
            prospect_revenue: Optional revenue figure

        Returns:
            ProspectBenchmark with size comparison and ICP fit
        """
        benchmarks = await self.get_industry_benchmarks(naics_code)
        if not benchmarks:
            return None

        # Determine size percentile
        avg_emp = benchmarks.avg_employees_per_firm
        if prospect_employees < avg_emp * 0.5:
            size_percentile = "small"
        elif prospect_employees < avg_emp * 1.5:
            size_percentile = "medium"
        else:
            size_percentile = "large"

        # ICP fit: 20-150 employees (Cardinal Element target)
        icp_fit = 20 <= prospect_employees <= 150

        signals = []

        # Generate signals
        if icp_fit:
            signals.append(f"Employee count ({prospect_employees}) in ICP range (20-150)")
        elif prospect_employees < 20:
            signals.append(f"Employee count ({prospect_employees}) below ICP minimum (20)")
        else:
            signals.append(f"Employee count ({prospect_employees}) above ICP maximum (150)")

        if size_percentile == "medium":
            signals.append("Company size is typical for industry")
        elif size_percentile == "large":
            signals.append(f"Company is larger than industry average ({avg_emp:.0f} employees)")
        else:
            signals.append(f"Company is smaller than industry average ({avg_emp:.0f} employees)")

        # Check if NAICS is in ICP target industries
        if naics_code in ICP_NAICS_CODES:
            signals.append(f"Industry ({ICP_NAICS_CODES[naics_code]}) is ICP target")
        else:
            signals.append("Industry not in primary ICP target list")

        return ProspectBenchmark(
            prospect_employees=prospect_employees,
            prospect_revenue=prospect_revenue,
            industry_avg_employees=avg_emp,
            industry_avg_payroll_per_employee=benchmarks.avg_payroll_per_employee,
            size_percentile=size_percentile,
            icp_fit=icp_fit,
            signals=signals,
        )

    async def get_top_states_for_industry(
        self,
        naics_code: str,
        limit: int = 10
    ) -> list[StateBusinessData]:
        """Get top states by establishment count for an industry.

        Useful for geographic targeting in sales.

        Args:
            naics_code: 6-digit NAICS industry code
            limit: Number of states to return

        Returns:
            List of StateBusinessData sorted by establishment count
        """
        all_states = await self.get_all_states_data(naics_code)
        return all_states[:limit]

    def lookup_naics_code(self, description: str) -> list[tuple[str, str]]:
        """Search for NAICS codes by description.

        Args:
            description: Search term (e.g., "consulting", "engineering")

        Returns:
            List of (code, description) tuples matching search
        """
        description = description.lower()
        matches = []
        for code, desc in ICP_NAICS_CODES.items():
            if description in desc.lower():
                matches.append((code, desc))
        return matches


class CensusAPIError(Exception):
    """Exception raised for Census API errors."""

    pass
