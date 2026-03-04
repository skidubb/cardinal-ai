"""
Tool Registry for C-Suite Agent Function Calling.

Maps agent roles to their allowed tools and provides async handlers
that instantiate tool clients, call methods, and return JSON strings.

All tools are read-only. Errors are returned as {"error": "..."} strings
so Claude can see and adjust — handlers never raise.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from csuite.tools.schemas import ALL_TOOL_SCHEMAS

logger = logging.getLogger(__name__)

# Maximum characters in a tool result before truncation
MAX_RESULT_LENGTH = 50_000

# Maximum input string length for any single parameter
MAX_INPUT_STRING_LENGTH = 500

# =============================================================================
# Role -> Tool Mapping
# =============================================================================

# Tools available to all agents
_COMMON_TOOLS = [
    "web_search",
    "web_fetch",
    "notion_search",
    "write_deliverable",
    "export_pdf",
    "qa_validate",
]

ROLE_TOOL_MAP: dict[str, list[str]] = {
    "cfo": [
        "pricing_calculate_audit",
        "pricing_calculate_implementation",
        "pricing_calculate_retainer",
        "sec_search_companies",
        "sec_get_financials",
        "sec_get_filings",
        "pinecone_search_knowledge",
        *_COMMON_TOOLS,
    ],
    "cto": [
        "github_get_org",
        "github_analyze_tech_stack",
        "github_assess_engineering_maturity",
        "github_generate_prospect_profile",
        "pinecone_search_knowledge",
        *_COMMON_TOOLS,
    ],
    "ceo": [
        "sec_search_companies",
        "sec_get_financials",
        "sec_get_filings",
        "sec_generate_prospect_brief",
        "census_estimate_market_size",
        "pinecone_search_knowledge",
        *_COMMON_TOOLS,
    ],
    "cmo": [
        "census_estimate_market_size",
        "census_get_industry_benchmarks",
        "bls_assess_labor_market",
        "pinecone_search_knowledge",
        "openai_generate_image",
        "gemini_generate_image",
        *_COMMON_TOOLS,
    ],
    "coo": [
        "bls_get_employment_trend",
        "bls_assess_labor_market",
        "census_benchmark_prospect",
        "pinecone_search_knowledge",
        "notion_query_database",
        "notion_create_page",
        *_COMMON_TOOLS,
    ],
    "cpo": [
        "census_get_industry_benchmarks",
        "pricing_calculate_audit",
        "pricing_calculate_implementation",
        "pricing_calculate_retainer",
        "pinecone_search_knowledge",
        "openai_generate_image",
        "gemini_generate_image",
        *_COMMON_TOOLS,
    ],
    "cro": [
        "sec_search_companies",
        "sec_get_financials",
        "sec_get_filings",
        "pricing_calculate_audit",
        "pricing_calculate_implementation",
        "pricing_calculate_retainer",
        "census_estimate_market_size",
        "pinecone_search_knowledge",
        *_COMMON_TOOLS,
    ],
    # --- CEO Direct Reports (inherit CEO tools) ---
    "ceo-board-prep": [
        "sec_search_companies", "sec_get_financials", "sec_get_filings",
        "sec_generate_prospect_brief", "census_estimate_market_size",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "ceo-competitive-intel": [
        "sec_search_companies", "sec_get_financials", "sec_get_filings",
        "sec_generate_prospect_brief", "census_estimate_market_size",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "ceo-deal-strategist": [
        "sec_search_companies", "sec_get_financials", "sec_get_filings",
        "sec_generate_prospect_brief", "census_estimate_market_size",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    # --- CFO Direct Reports (inherit CFO tools) ---
    "cfo-cash-flow-forecaster": [
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "sec_search_companies", "sec_get_financials",
        "sec_get_filings", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cfo-client-profitability": [
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "sec_search_companies", "sec_get_financials",
        "sec_get_filings", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cfo-pricing-strategist": [
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "sec_search_companies", "sec_get_financials",
        "sec_get_filings", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    # --- CMO Direct Reports (inherit CMO tools) ---
    "cmo-brand-designer": [
        "census_estimate_market_size", "census_get_industry_benchmarks",
        "bls_assess_labor_market", "pinecone_search_knowledge",
        "openai_generate_image", "gemini_generate_image", *_COMMON_TOOLS,
    ],
    "cmo-distribution-strategist": [
        "census_estimate_market_size", "census_get_industry_benchmarks",
        "bls_assess_labor_market", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cmo-linkedin-ghostwriter": [
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cmo-market-intel": [
        "census_estimate_market_size", "census_get_industry_benchmarks",
        "bls_assess_labor_market", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cmo-outbound-campaign": [
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cmo-thought-leadership": [
        "census_estimate_market_size", "census_get_industry_benchmarks",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    # --- COO Direct Reports (inherit COO tools) ---
    "coo-bench-coordinator": [
        "bls_get_employment_trend", "bls_assess_labor_market",
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    "coo-engagement-manager": [
        "bls_get_employment_trend", "bls_assess_labor_market",
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    "coo-process-builder": [
        "bls_get_employment_trend", "bls_assess_labor_market",
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    # --- CPO Direct Reports (inherit CPO tools) ---
    "cpo-client-insights": [
        "census_get_industry_benchmarks", "pricing_calculate_audit",
        "pricing_calculate_implementation", "pricing_calculate_retainer",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cpo-deliverable-designer": [
        "census_get_industry_benchmarks", "pricing_calculate_audit",
        "pricing_calculate_implementation", "pricing_calculate_retainer",
        "pinecone_search_knowledge", "openai_generate_image",
        "gemini_generate_image", *_COMMON_TOOLS,
    ],
    "cpo-service-designer": [
        "census_get_industry_benchmarks", "pricing_calculate_audit",
        "pricing_calculate_implementation", "pricing_calculate_retainer",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    # --- CTO Direct Reports (inherit CTO tools) ---
    "cto-ai-systems-designer": [
        "github_get_org", "github_analyze_tech_stack",
        "github_assess_engineering_maturity", "github_generate_prospect_profile",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cto-audit-architect": [
        "github_get_org", "github_analyze_tech_stack",
        "github_assess_engineering_maturity", "github_generate_prospect_profile",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "cto-internal-platform": [
        "github_get_org", "github_analyze_tech_stack",
        "github_assess_engineering_maturity", "github_generate_prospect_profile",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    # --- GTM Leadership (inherit CRO tools) ---
    "gtm-cro": [
        "sec_search_companies", "sec_get_financials", "sec_get_filings",
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "census_estimate_market_size",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-vp-sales": [
        "sec_search_companies", "sec_get_financials", "sec_get_filings",
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-vp-growth-ops": [
        "census_estimate_market_size", "census_get_industry_benchmarks",
        "bls_assess_labor_market", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-vp-partnerships": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-vp-revops": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-vp-success": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    # --- GTM Sales & Pipeline ---
    "gtm-ae-strategist": [
        "sec_search_companies", "sec_get_financials",
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-deal-desk": [
        "sec_search_companies", "sec_get_financials",
        "pricing_calculate_audit", "pricing_calculate_implementation",
        "pricing_calculate_retainer", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-sales-ops": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-sdr-manager": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-sdr-agent": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    # --- GTM Marketing & Demand Gen ---
    "gtm-abm-specialist": [
        "census_estimate_market_size", "census_get_industry_benchmarks",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-content-marketer": [
        "census_estimate_market_size", "bls_assess_labor_market",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-demand-gen": [
        "census_estimate_market_size", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-analytics": [
        "sec_search_companies", "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    "gtm-revenue-analyst": [
        "sec_search_companies", "sec_get_financials",
        "pinecone_search_knowledge", *_COMMON_TOOLS,
    ],
    # --- GTM Partners & Channels ---
    "gtm-partner-manager": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-partner-enablement": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-alliance-ops": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "gtm-channel-marketer": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    # --- GTM Customer Success & Retention ---
    "gtm-csm-lead": [
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    "gtm-onboarding-specialist": [
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    "gtm-renewals-manager": [
        "pinecone_search_knowledge", "notion_query_database", *_COMMON_TOOLS,
    ],
    # --- GTM Operations & Infrastructure ---
    "gtm-data-ops": [
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    "gtm-systems-admin": [
        "pinecone_search_knowledge", "notion_query_database",
        "notion_create_page", *_COMMON_TOOLS,
    ],
    # --- External Perspectives ---
    "vc-app-investor": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "vc-infra-investor": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "brand-essence": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    # --- Airport 5G Decision-Maker Simulation Agents ---
    "airport-cio": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "airport-cro": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "airline-ops-vp": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "cargo-ops-director": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "concessions-tech-lead": ["pinecone_search_knowledge", *_COMMON_TOOLS],
    "att-carrier-rep": ["pinecone_search_knowledge", *_COMMON_TOOLS],
}


# =============================================================================
# Output Sanitization
# =============================================================================

# Patterns that could be used for prompt injection via tool results
_DANGEROUS_TAG_PATTERN = re.compile(
    r"<\s*/?\s*(?:system|human|assistant|tool_result|function_call|prompt)\s*[^>]*>",
    re.IGNORECASE,
)

# ANSI escape codes
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# Unicode direction overrides and zero-width characters
_UNICODE_CONTROL_PATTERN = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f"  # Zero-width and direction marks
    "\u202a\u202b\u202c\u202d\u202e"   # Direction overrides
    "\u2066\u2067\u2068\u2069"         # Isolates
    "\ufeff"                           # BOM / zero-width no-break space
    "]"
)


def sanitize_tool_output(text: str) -> str:
    """Strip potentially dangerous patterns from tool output.

    Removes:
    - XML-like tags that could mimic system prompts
    - ANSI escape codes
    - Null bytes and control characters (except standard whitespace)
    - Unicode direction overrides and zero-width characters
    """
    # Strip null bytes and control chars (keep \t \n \r)
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    text = _DANGEROUS_TAG_PATTERN.sub("", text)
    text = _ANSI_PATTERN.sub("", text)
    text = _UNICODE_CONTROL_PATTERN.sub("", text)

    if len(text) > MAX_RESULT_LENGTH:
        text = text[:MAX_RESULT_LENGTH] + f"\n[TRUNCATED — original length: {len(text)} chars]"
    return text


def _validate_string_input(value: Any, param_name: str) -> str:
    """Validate a string input parameter."""
    if not isinstance(value, str):
        raise ValueError(f"{param_name} must be a string")
    if len(value) > MAX_INPUT_STRING_LENGTH:
        raise ValueError(f"{param_name} exceeds maximum length of {MAX_INPUT_STRING_LENGTH}")
    return value


def _validate_int_input(
    value: Any, param_name: str, min_val: int = 0, max_val: int = 1_000_000
) -> int:
    """Validate an integer input parameter within bounds."""
    try:
        result = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{param_name} must be an integer") from e
    if result < min_val or result > max_val:
        raise ValueError(f"{param_name} must be between {min_val} and {max_val}")
    return result


def _validate_float_input(
    value: Any, param_name: str, min_val: float = 0.0, max_val: float = 1e12
) -> float:
    """Validate a float input parameter within bounds."""
    try:
        result = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{param_name} must be a number") from e
    if result < min_val or result > max_val:
        raise ValueError(f"{param_name} must be between {min_val} and {max_val}")
    return result


def _to_json(obj: Any) -> str:
    """Convert a dataclass or dict to JSON string."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return json.dumps(dataclasses.asdict(obj), default=str)
    if isinstance(obj, list):
        return json.dumps(
            [dataclasses.asdict(item) if dataclasses.is_dataclass(item) else item for item in obj],
            default=str,
        )
    if isinstance(obj, dict):
        return json.dumps(obj, default=str)
    return json.dumps({"result": str(obj)}, default=str)


# =============================================================================
# Tool Handlers
# =============================================================================

async def _handle_sec_search_companies(tool_input: dict, settings: Any) -> str:
    from csuite.tools.sec_edgar import SECEdgarClient

    query = _validate_string_input(tool_input["query"], "query")
    limit = _validate_int_input(tool_input.get("limit", 10), "limit", 1, 100)
    client = SECEdgarClient()
    results = await client.search_companies(query, limit=limit)
    return _to_json(results)


async def _handle_sec_get_financials(tool_input: dict, settings: Any) -> str:
    from csuite.tools.sec_edgar import SECEdgarClient

    cik_or_ticker = _validate_string_input(tool_input["cik_or_ticker"], "cik_or_ticker")
    client = SECEdgarClient()
    result = await client.get_company_financials(cik_or_ticker)
    if result is None:
        return json.dumps({"error": f"No financial data found for '{cik_or_ticker}'"})
    return _to_json(result)


async def _handle_sec_get_filings(tool_input: dict, settings: Any) -> str:
    from csuite.tools.sec_edgar import SECEdgarClient

    cik_or_ticker = _validate_string_input(tool_input["cik_or_ticker"], "cik_or_ticker")
    form_types = tool_input.get("form_types")
    limit = _validate_int_input(tool_input.get("limit", 10), "limit", 1, 100)
    client = SECEdgarClient()
    results = await client.get_recent_filings(cik_or_ticker, form_types=form_types, limit=limit)
    return _to_json(results)


async def _handle_sec_generate_prospect_brief(tool_input: dict, settings: Any) -> str:
    from csuite.tools.sec_edgar import SECEdgarClient

    cik_or_ticker = _validate_string_input(tool_input["cik_or_ticker"], "cik_or_ticker")
    client = SECEdgarClient()
    result = await client.generate_prospect_brief(cik_or_ticker)
    return _to_json(result)


async def _handle_github_get_org(tool_input: dict, settings: Any) -> str:
    from csuite.tools.github_api import GitHubClient

    org_name = _validate_string_input(tool_input["org_name"], "org_name")
    client = GitHubClient(token=settings.github_token)
    result = await client.get_organization(org_name)
    if result is None:
        return json.dumps({"error": f"GitHub organization '{org_name}' not found"})
    return _to_json(result)


async def _handle_github_analyze_tech_stack(tool_input: dict, settings: Any) -> str:
    from csuite.tools.github_api import GitHubClient

    org_name = _validate_string_input(tool_input["org_name"], "org_name")
    max_repos = _validate_int_input(tool_input.get("max_repos", 20), "max_repos", 1, 100)
    client = GitHubClient(token=settings.github_token)
    result = await client.analyze_org_tech_stack(org_name, max_repos=max_repos)
    if result is None:
        return json.dumps({"error": f"No tech stack data for '{org_name}'"})
    return _to_json(result)


async def _handle_github_assess_engineering_maturity(tool_input: dict, settings: Any) -> str:
    from csuite.tools.github_api import GitHubClient

    org_name = _validate_string_input(tool_input["org_name"], "org_name")
    client = GitHubClient(token=settings.github_token)
    result = await client.assess_engineering_maturity(org_name)
    if result is None:
        return json.dumps({"error": f"No maturity data for '{org_name}'"})
    return _to_json(result)


async def _handle_github_generate_prospect_profile(tool_input: dict, settings: Any) -> str:
    from csuite.tools.github_api import GitHubClient

    org_name = _validate_string_input(tool_input["org_name"], "org_name")
    client = GitHubClient(token=settings.github_token)
    result = await client.generate_prospect_tech_profile(org_name)
    return _to_json(result)


async def _handle_census_estimate_market_size(tool_input: dict, settings: Any) -> str:
    from csuite.tools.census_api import CensusClient

    naics_code = _validate_string_input(tool_input["naics_code"], "naics_code")
    state = tool_input.get("state")
    client = CensusClient()
    result = await client.estimate_market_size(naics_code, state=state)
    if result is None:
        return json.dumps({"error": f"No market data for NAICS '{naics_code}'"})
    return _to_json(result)


async def _handle_census_get_industry_benchmarks(tool_input: dict, settings: Any) -> str:
    from csuite.tools.census_api import CensusClient

    naics_code = _validate_string_input(tool_input["naics_code"], "naics_code")
    client = CensusClient()
    result = await client.get_industry_benchmarks(naics_code)
    if result is None:
        return json.dumps({"error": f"No benchmark data for NAICS '{naics_code}'"})
    return _to_json(result)


async def _handle_census_benchmark_prospect(tool_input: dict, settings: Any) -> str:
    from csuite.tools.census_api import CensusClient

    prospect_employees = _validate_int_input(
        tool_input["prospect_employees"], "prospect_employees", 1, 10_000_000
    )
    naics_code = _validate_string_input(tool_input["naics_code"], "naics_code")
    prospect_revenue = tool_input.get("prospect_revenue")
    if prospect_revenue is not None:
        prospect_revenue = _validate_float_input(
            prospect_revenue, "prospect_revenue", 0.0, 1e12
        )
    client = CensusClient()
    result = await client.benchmark_prospect(prospect_employees, naics_code, prospect_revenue)
    if result is None:
        return json.dumps({"error": f"No benchmark data for NAICS '{naics_code}'"})
    return _to_json(result)


async def _handle_bls_get_employment_trend(tool_input: dict, settings: Any) -> str:
    from csuite.tools.bls_api import BLSClient

    naics_code = _validate_string_input(tool_input["naics_code"], "naics_code")
    months = _validate_int_input(tool_input.get("months", 12), "months", 1, 120)
    client = BLSClient()
    result = await client.get_employment_trend(naics_code, months=months)
    if result is None:
        return json.dumps({"error": f"Insufficient employment data for NAICS '{naics_code}'"})
    return _to_json(result)


async def _handle_bls_assess_labor_market(tool_input: dict, settings: Any) -> str:
    from csuite.tools.bls_api import BLSClient

    naics_code = _validate_string_input(tool_input["naics_code"], "naics_code")
    client = BLSClient()
    result = await client.assess_labor_market(naics_code)
    if result is None:
        return json.dumps({"error": f"Insufficient labor data for NAICS '{naics_code}'"})
    return _to_json(result)


async def _handle_pricing_calculate_audit(tool_input: dict, settings: Any) -> str:
    from csuite.tools.pricing_calculator import (
        ComplexityLevel,
        IndustryVertical,
        PricingCalculator,
    )

    calc = PricingCalculator()
    kwargs: dict[str, Any] = {}
    if "complexity" in tool_input:
        kwargs["complexity"] = ComplexityLevel(tool_input["complexity"])
    if "industry" in tool_input:
        kwargs["industry"] = IndustryVertical(tool_input["industry"])
    if "timeline_weeks" in tool_input:
        kwargs["timeline_weeks"] = _validate_int_input(
            tool_input["timeline_weeks"], "timeline_weeks", 1, 52
        )
    if "client_revenue" in tool_input:
        kwargs["client_revenue"] = _validate_float_input(
            tool_input["client_revenue"], "client_revenue", 0.0, 1e12
        )
    result = calc.calculate_audit_price(**kwargs)
    return json.dumps(result.to_dict(), default=str)


async def _handle_pricing_calculate_implementation(tool_input: dict, settings: Any) -> str:
    from csuite.tools.pricing_calculator import (
        ComplexityLevel,
        IndustryVertical,
        PricingCalculator,
    )

    calc = PricingCalculator()
    kwargs: dict[str, Any] = {}
    if "complexity" in tool_input:
        kwargs["complexity"] = ComplexityLevel(tool_input["complexity"])
    if "industry" in tool_input:
        kwargs["industry"] = IndustryVertical(tool_input["industry"])
    if "timeline_weeks" in tool_input:
        kwargs["timeline_weeks"] = _validate_int_input(
            tool_input["timeline_weeks"], "timeline_weeks", 1, 104
        )
    if "scope_description" in tool_input:
        kwargs["scope_description"] = _validate_string_input(
            tool_input["scope_description"], "scope_description"
        )
    if "client_revenue" in tool_input:
        kwargs["client_revenue"] = _validate_float_input(
            tool_input["client_revenue"], "client_revenue", 0.0, 1e12
        )
    result = calc.calculate_implementation_price(**kwargs)
    return json.dumps(result.to_dict(), default=str)


async def _handle_pricing_calculate_retainer(tool_input: dict, settings: Any) -> str:
    from csuite.tools.pricing_calculator import (
        ComplexityLevel,
        PricingCalculator,
    )

    calc = PricingCalculator()
    kwargs: dict[str, Any] = {}
    if "complexity" in tool_input:
        kwargs["complexity"] = ComplexityLevel(tool_input["complexity"])
    if "commitment_months" in tool_input:
        kwargs["commitment_months"] = _validate_int_input(
            tool_input["commitment_months"], "commitment_months", 1, 36
        )
    if "hours_per_month" in tool_input:
        kwargs["hours_per_month"] = _validate_int_input(
            tool_input["hours_per_month"], "hours_per_month", 1, 200
        )
    if "client_revenue" in tool_input:
        kwargs["client_revenue"] = _validate_float_input(
            tool_input["client_revenue"], "client_revenue", 0.0, 1e12
        )
    result = calc.calculate_retainer_price(**kwargs)
    return json.dumps(result.to_dict(), default=str)


async def _handle_pinecone_search_knowledge(tool_input: dict, settings: Any) -> str:
    from csuite.tools.pinecone_kb import handle_pinecone_search

    return await handle_pinecone_search(tool_input, settings)


async def _handle_openai_generate_image(tool_input: dict, settings: Any) -> str:
    from csuite.tools.image_gen import generate_image_openai

    prompt = _validate_string_input(tool_input["prompt"], "prompt")
    size = tool_input.get("size", "auto")
    quality = tool_input.get("quality", "medium")
    style = tool_input.get("style")
    result = await generate_image_openai(
        prompt=prompt, size=size, quality=quality, style=style, api_key=settings.openai_api_key,
    )
    return json.dumps(result, default=str)


async def _handle_gemini_generate_image(tool_input: dict, settings: Any) -> str:
    from csuite.tools.image_gen import generate_image_gemini

    prompt = _validate_string_input(tool_input["prompt"], "prompt")
    size = tool_input.get("size", "1024x1024")
    result = await generate_image_gemini(
        prompt=prompt, size=size, api_key=settings.gemini_api_key,
    )
    return json.dumps(result, default=str)


async def _handle_web_search(tool_input: dict, settings: Any) -> str:
    from csuite.tools.web_search import brave_web_search

    query = _validate_string_input(tool_input["query"], "query")
    count = _validate_int_input(tool_input.get("count", 5), "count", 1, 20)
    result = await brave_web_search(query=query, count=count, api_key=settings.brave_api_key)
    return json.dumps(result, default=str)


async def _handle_web_fetch(tool_input: dict, settings: Any) -> str:
    from csuite.tools.web_search import fetch_web_page

    url = _validate_string_input(tool_input["url"], "url")
    result = await fetch_web_page(url=url, api_key=settings.brave_api_key)
    return json.dumps(result, default=str)


async def _handle_notion_search(tool_input: dict, settings: Any) -> str:
    from csuite.tools.notion_api import notion_search

    query = _validate_string_input(tool_input["query"], "query")
    filter_type = tool_input.get("filter_type")
    result = await notion_search(
        query=query, filter_type=filter_type, api_key=settings.notion_api_key,
    )
    return json.dumps(result, default=str)


async def _handle_notion_query_database(tool_input: dict, settings: Any) -> str:
    from csuite.tools.notion_api import notion_query_database

    database_id = _validate_string_input(tool_input["database_id"], "database_id")
    filter_obj = tool_input.get("filter")
    sorts = tool_input.get("sorts")
    result = await notion_query_database(
        database_id=database_id, filter=filter_obj, sorts=sorts, api_key=settings.notion_api_key,
    )
    return json.dumps(result, default=str)


async def _handle_notion_create_page(tool_input: dict, settings: Any) -> str:
    from csuite.tools.notion_api import notion_create_page

    parent_id = _validate_string_input(tool_input["parent_id"], "parent_id")
    title = _validate_string_input(tool_input["title"], "title")
    content = tool_input.get("content")
    properties = tool_input.get("properties")
    result = await notion_create_page(
        parent_id=parent_id, title=title, content=content,
        properties=properties, api_key=settings.notion_api_key,
    )
    return json.dumps(result, default=str)


async def _handle_write_deliverable(tool_input: dict, settings: Any) -> str:
    import re

    filename = _validate_string_input(tool_input["filename"], "filename")
    content = tool_input["content"]
    if not isinstance(content, str):
        return json.dumps({"error": "content must be a string"})
    directory = tool_input.get("directory", "deliverables")
    if isinstance(directory, str):
        # Sanitize directory name
        directory = directory.strip().replace("..", "").strip("/")
    else:
        directory = "deliverables"

    # Validate naming convention (warn, don't block)
    naming_pattern = r"^[A-Z]{2,3}-D\d+-[\w-]+\.md$"
    warning = ""
    if not re.match(naming_pattern, filename):
        warning = (
            f"Warning: '{filename}' does not match naming convention "
            "({EXEC}-D{N}-{ShortName}.md). File saved anyway."
        )

    output_dir = settings.reports_dir / directory
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename
    filepath.write_text(content)

    result: dict[str, Any] = {"path": str(filepath), "bytes": len(content.encode())}
    if warning:
        result["warning"] = warning
    return json.dumps(result, default=str)


async def _handle_export_pdf(tool_input: dict, settings: Any) -> str:
    from pathlib import Path

    markdown_path = _validate_string_input(tool_input["markdown_path"], "markdown_path")
    md_file = Path(markdown_path)
    if not md_file.exists():
        return json.dumps({"error": f"File not found: {markdown_path}"})

    content = md_file.read_text()

    from csuite.tools.report_generator import ProspectReportGenerator
    generator = ProspectReportGenerator(output_dir=md_file.parent)
    pdf_path = md_file.with_suffix(".pdf")
    result = generator.save_pdf(content, pdf_path)
    if result is None:
        return json.dumps({
            "error": "PDF export requires weasyprint. Install: pip install weasyprint markdown"
        })
    return json.dumps({"path": str(result), "pages": "N/A"}, default=str)


async def _handle_qa_validate(tool_input: dict, settings: Any) -> str:
    from csuite.tools.qa_protocol import AgentOutput, QAPipeline

    content = tool_input["content"]
    if not isinstance(content, str):
        return json.dumps({"error": "content must be a string"})
    if len(content) < 50:
        return json.dumps({
            "error": "Content too short for QA validation (minimum 50 chars)"
        })

    tier = tool_input.get("tier", "all")
    context = tool_input.get("context", "")

    output = AgentOutput(
        content=content,
        output_type="deliverable",
        agent_role="unknown",
        engagement_context=context,
    )

    pipeline = QAPipeline()

    if tier == "1":
        eval_result = await pipeline.run_tier1_only(output)
        return json.dumps({
            "tier_1": eval_result.to_dict(),
            "overall_pass": eval_result.result.value == "approved",
        }, default=str)
    elif tier == "2":
        result = await pipeline.run_through_tier2(output)
        return json.dumps(result.to_dict(), default=str)
    elif tier == "3":
        # Run all tiers up through 3
        result = await pipeline.run(output)
        return json.dumps(result.to_dict(), default=str)
    else:
        # "all" — run full pipeline
        result = await pipeline.run(output)
        return json.dumps(result.to_dict(), default=str)


# Handler dispatch table
TOOL_HANDLERS: dict[str, Callable] = {
    "sec_search_companies": _handle_sec_search_companies,
    "sec_get_financials": _handle_sec_get_financials,
    "sec_get_filings": _handle_sec_get_filings,
    "sec_generate_prospect_brief": _handle_sec_generate_prospect_brief,
    "github_get_org": _handle_github_get_org,
    "github_analyze_tech_stack": _handle_github_analyze_tech_stack,
    "github_assess_engineering_maturity": _handle_github_assess_engineering_maturity,
    "github_generate_prospect_profile": _handle_github_generate_prospect_profile,
    "census_estimate_market_size": _handle_census_estimate_market_size,
    "census_get_industry_benchmarks": _handle_census_get_industry_benchmarks,
    "census_benchmark_prospect": _handle_census_benchmark_prospect,
    "bls_get_employment_trend": _handle_bls_get_employment_trend,
    "bls_assess_labor_market": _handle_bls_assess_labor_market,
    "pricing_calculate_audit": _handle_pricing_calculate_audit,
    "pricing_calculate_implementation": _handle_pricing_calculate_implementation,
    "pricing_calculate_retainer": _handle_pricing_calculate_retainer,
    "pinecone_search_knowledge": _handle_pinecone_search_knowledge,
    "openai_generate_image": _handle_openai_generate_image,
    "gemini_generate_image": _handle_gemini_generate_image,
    "web_search": _handle_web_search,
    "web_fetch": _handle_web_fetch,
    "notion_search": _handle_notion_search,
    "notion_query_database": _handle_notion_query_database,
    "notion_create_page": _handle_notion_create_page,
    "write_deliverable": _handle_write_deliverable,
    "export_pdf": _handle_export_pdf,
    "qa_validate": _handle_qa_validate,
}


# =============================================================================
# Public API
# =============================================================================

def get_tools_for_role(role: str, settings: Any | None = None) -> list[dict]:
    """Get Anthropic tool definitions for an agent role.

    Returns empty list if role has no tools or tools are disabled.
    Filters out tools that require unavailable API keys.
    """
    tool_names = ROLE_TOOL_MAP.get(role.lower(), [])
    if not tool_names:
        return []

    tools = []
    for name in tool_names:
        schema = ALL_TOOL_SCHEMAS.get(name)
        if schema:
            # Filter out GitHub tools if no token (they'll fail with 60 req/hr)
            # but still include them — they work without token, just rate-limited
            tools.append(schema)

    return tools


async def execute_tool(
    tool_name: str,
    tool_input: dict,
    settings: Any,
    cost_tracker: Any | None = None,
) -> str:
    """Execute a tool and return sanitized JSON string result.

    Never raises — errors are returned as {"error": "..."} strings.
    """
    start_time = time.monotonic()
    success = False

    try:
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        result = await handler(tool_input, settings)
        result = sanitize_tool_output(result)
        success = True
        return result

    except Exception as e:
        logger.warning("Tool %s failed: %s", tool_name, e, exc_info=True)
        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(e)[:200]}"})

    finally:
        elapsed = time.monotonic() - start_time
        if cost_tracker:
            try:
                cost_tracker.log_usage(
                    agent="TOOL",
                    model="tool_call",
                    input_tokens=0,
                    output_tokens=0,
                    metadata={
                        "tool_name": tool_name,
                        "tool_input": {k: str(v)[:100] for k, v in tool_input.items()},
                        "execution_time_ms": round(elapsed * 1000),
                        "success": success,
                    },
                )
            except Exception:
                pass
