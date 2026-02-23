"""
Custom MCP tools for C-Suite agents.
"""

from csuite.tools.bls_api import (
    NAICS_TO_BLS_SERIES,
    OCCUPATION_CODES,
    BLSAPIError,
    BLSClient,
    CPIData,
    EmploymentTrend,
    IndustryEmployment,
    IndustryWages,
    LaborMarketAssessment,
    OccupationWages,
)
from csuite.tools.census_api import (
    ICP_NAICS_CODES,
    CensusAPIError,
    CensusClient,
    IndustryBenchmarks,
    MarketSizeEstimate,
    ProspectBenchmark,
    StateBusinessData,
    ZipCodeData,
)
from csuite.tools.github_api import (
    ActivityMetrics,
    ContributorInfo,
    EngineeringMaturity,
    GitHubAPIError,
    GitHubClient,
    OrganizationInfo,
    ProspectTechProfile,
    RepositoryInfo,
    TechStackAnalysis,
)
from csuite.tools.quickbooks_mcp import QuickBooksMCP
from csuite.tools.registry import execute_tool, get_tools_for_role
from csuite.tools.sec_edgar import (
    CompanyInfo,
    Filing,
    FinancialData,
    FormDFiling,
    ProspectResearchBrief,
    SECEdgarClient,
    SECEdgarError,
)

__all__ = [
    # Tool Registry
    "get_tools_for_role",
    "execute_tool",
    # QuickBooks
    "QuickBooksMCP",
    # SEC EDGAR
    "SECEdgarClient",
    "SECEdgarError",
    "CompanyInfo",
    "Filing",
    "FinancialData",
    "FormDFiling",
    "ProspectResearchBrief",
    # Census Bureau
    "CensusClient",
    "CensusAPIError",
    "IndustryBenchmarks",
    "StateBusinessData",
    "ZipCodeData",
    "MarketSizeEstimate",
    "ProspectBenchmark",
    "ICP_NAICS_CODES",
    # Bureau of Labor Statistics
    "BLSClient",
    "BLSAPIError",
    "IndustryEmployment",
    "EmploymentTrend",
    "OccupationWages",
    "IndustryWages",
    "CPIData",
    "LaborMarketAssessment",
    "NAICS_TO_BLS_SERIES",
    "OCCUPATION_CODES",
    # GitHub
    "GitHubClient",
    "GitHubAPIError",
    "OrganizationInfo",
    "RepositoryInfo",
    "TechStackAnalysis",
    "ContributorInfo",
    "ActivityMetrics",
    "EngineeringMaturity",
    "ProspectTechProfile",
]
