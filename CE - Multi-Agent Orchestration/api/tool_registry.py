"""Static catalog of tools, MCP servers, and role-based mappings.

Each tool entry carries:
  - name: internal tool identifier
  - description: one-line human-readable
  - domain: functional grouping (sec_edgar, github, pricing, notion, ...)
  - direction: "input" (reads/fetches), "output" (writes/produces), "internal" (QA/validation)
  - brand: simple-icons slug for logo rendering, or "" for proprietary/no-brand

Consumers (frontend marketplace, agent builder) group tools by `direction` and
render logos from `brand`.
"""

# ── Tool Catalog ─────────────────────────────────────────────────────────────

TOOL_CATALOG = {
    "sec_search_companies": {
        "name": "sec_search_companies",
        "description": "Search SEC EDGAR for public companies by name",
        "domain": "sec_edgar",
        "direction": "input",
        "brand": "",
    },
    "sec_get_financials": {
        "name": "sec_get_financials",
        "description": "Get financial statements for a public company",
        "domain": "sec_edgar",
        "direction": "input",
        "brand": "",
    },
    "sec_get_filings": {
        "name": "sec_get_filings",
        "description": "Get recent SEC filings for a company",
        "domain": "sec_edgar",
        "direction": "input",
        "brand": "",
    },
    "sec_generate_prospect_brief": {
        "name": "sec_generate_prospect_brief",
        "description": "Generate a prospect brief from SEC data",
        "domain": "sec_edgar",
        "direction": "output",
        "brand": "",
    },
    "github_get_org": {
        "name": "github_get_org",
        "description": "Get GitHub organization profile and repos",
        "domain": "github",
        "direction": "input",
        "brand": "github",
    },
    "github_analyze_tech_stack": {
        "name": "github_analyze_tech_stack",
        "description": "Analyze tech stack from GitHub repos",
        "domain": "github",
        "direction": "input",
        "brand": "github",
    },
    "github_assess_engineering_maturity": {
        "name": "github_assess_engineering_maturity",
        "description": "Assess engineering maturity from GitHub signals",
        "domain": "github",
        "direction": "input",
        "brand": "github",
    },
    "github_generate_prospect_profile": {
        "name": "github_generate_prospect_profile",
        "description": "Generate prospect profile from GitHub data",
        "domain": "github",
        "direction": "output",
        "brand": "github",
    },
    "census_estimate_market_size": {
        "name": "census_estimate_market_size",
        "description": "Estimate market size using Census Bureau data",
        "domain": "census",
        "direction": "input",
        "brand": "",
    },
    "census_get_industry_benchmarks": {
        "name": "census_get_industry_benchmarks",
        "description": "Get industry benchmarks from Census data",
        "domain": "census",
        "direction": "input",
        "brand": "",
    },
    "census_benchmark_prospect": {
        "name": "census_benchmark_prospect",
        "description": "Benchmark a prospect against Census industry data",
        "domain": "census",
        "direction": "output",
        "brand": "",
    },
    "bls_get_employment_trend": {
        "name": "bls_get_employment_trend",
        "description": "Get employment trends from Bureau of Labor Statistics",
        "domain": "bls",
        "direction": "input",
        "brand": "",
    },
    "bls_assess_labor_market": {
        "name": "bls_assess_labor_market",
        "description": "Assess labor market conditions from BLS data",
        "domain": "bls",
        "direction": "input",
        "brand": "",
    },
    "pricing_calculate_audit": {
        "name": "pricing_calculate_audit",
        "description": "Calculate pricing for a CE audit engagement",
        "domain": "pricing",
        "direction": "output",
        "brand": "",
    },
    "pricing_calculate_implementation": {
        "name": "pricing_calculate_implementation",
        "description": "Calculate pricing for a CE implementation engagement",
        "domain": "pricing",
        "direction": "output",
        "brand": "",
    },
    "pricing_calculate_retainer": {
        "name": "pricing_calculate_retainer",
        "description": "Calculate pricing for a CE retainer engagement",
        "domain": "pricing",
        "direction": "output",
        "brand": "",
    },
    "pinecone_search_knowledge": {
        "name": "pinecone_search_knowledge",
        "description": "Search the Pinecone knowledge base",
        "domain": "pinecone",
        "direction": "input",
        "brand": "pinecone",
    },
    "openai_generate_image": {
        "name": "openai_generate_image",
        "description": "Generate an image using OpenAI DALL-E",
        "domain": "image_gen",
        "direction": "output",
        "brand": "openai",
    },
    "gemini_generate_image": {
        "name": "gemini_generate_image",
        "description": "Generate an image using Google Gemini",
        "domain": "image_gen",
        "direction": "output",
        "brand": "googlegemini",
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web for information",
        "domain": "web",
        "direction": "input",
        "brand": "",
    },
    "web_fetch": {
        "name": "web_fetch",
        "description": "Fetch and extract content from a URL",
        "domain": "web",
        "direction": "input",
        "brand": "",
    },
    "notion_search": {
        "name": "notion_search",
        "description": "Search Notion workspace",
        "domain": "notion",
        "direction": "input",
        "brand": "notion",
    },
    "notion_query_database": {
        "name": "notion_query_database",
        "description": "Query a Notion database",
        "domain": "notion",
        "direction": "input",
        "brand": "notion",
    },
    "notion_create_page": {
        "name": "notion_create_page",
        "description": "Create a page in Notion",
        "domain": "notion",
        "direction": "output",
        "brand": "notion",
    },
    "write_deliverable": {
        "name": "write_deliverable",
        "description": "Write a structured deliverable document",
        "domain": "output",
        "direction": "output",
        "brand": "",
    },
    "export_pdf": {
        "name": "export_pdf",
        "description": "Export a deliverable as PDF",
        "domain": "output",
        "direction": "output",
        "brand": "adobeacrobatreader",
    },
    "qa_validate": {
        "name": "qa_validate",
        "description": "Validate output quality against criteria",
        "domain": "qa",
        "direction": "internal",
        "brand": "",
    },
}

# ── MCP Server Catalog ───────────────────────────────────────────────────────

MCP_SERVER_CATALOG = {
    "pinecone": {
        "name": "Pinecone",
        "description": "Vector knowledge base (ce-gtm-knowledge)",
        "transport": "stdio",
        "brand": "pinecone",
    },
    "notion": {
        "name": "Notion",
        "description": "Notion workspace read/write",
        "transport": "http",
        "brand": "notion",
    },
    "sec-edgar": {
        "name": "SEC EDGAR",
        "description": "SEC filings and company data",
        "transport": "stdio",
        "brand": "",
    },
    "pricing-calculator": {
        "name": "Pricing Calculator",
        "description": "CE engagement pricing models",
        "transport": "stdio",
        "brand": "",
    },
    "github-intel": {
        "name": "GitHub Intel",
        "description": "GitHub org analysis and tech stack profiling",
        "transport": "stdio",
        "brand": "github",
    },
}

# ── Role → Tool Mapping ─────────────────────────────────────────────────────

_COMMON_TOOLS = ["web_search", "web_fetch", "notion_search", "write_deliverable", "export_pdf", "qa_validate"]

ROLE_TOOL_MAP = {
    "ceo": ["sec_search_companies", "sec_get_financials", "sec_get_filings", "sec_generate_prospect_brief", "census_estimate_market_size", "pinecone_search_knowledge", *_COMMON_TOOLS],
    "cfo": ["pricing_calculate_audit", "pricing_calculate_implementation", "pricing_calculate_retainer", "sec_search_companies", "sec_get_financials", "sec_get_filings", "pinecone_search_knowledge", *_COMMON_TOOLS],
    "cto": ["github_get_org", "github_analyze_tech_stack", "github_assess_engineering_maturity", "github_generate_prospect_profile", "pinecone_search_knowledge", *_COMMON_TOOLS],
    "cmo": ["census_estimate_market_size", "census_get_industry_benchmarks", "bls_assess_labor_market", "pinecone_search_knowledge", "openai_generate_image", "gemini_generate_image", *_COMMON_TOOLS],
    "coo": ["bls_get_employment_trend", "bls_assess_labor_market", "census_benchmark_prospect", "pinecone_search_knowledge", "notion_query_database", "notion_create_page", *_COMMON_TOOLS],
    "cpo": ["census_get_industry_benchmarks", "pricing_calculate_audit", "pricing_calculate_implementation", "pricing_calculate_retainer", "pinecone_search_knowledge", "openai_generate_image", "gemini_generate_image", *_COMMON_TOOLS],
    "cro": ["sec_search_companies", "sec_get_financials", "sec_get_filings", "pricing_calculate_audit", "pricing_calculate_implementation", "pricing_calculate_retainer", "census_estimate_market_size", "pinecone_search_knowledge", *_COMMON_TOOLS],
}

# ── Role → MCP Server Mapping ───────────────────────────────────────────────

ROLE_MCP_MAP = {
    "ceo": ["pinecone", "notion"],
    "cfo": ["pinecone", "notion", "sec-edgar", "pricing-calculator"],
    "cto": ["pinecone", "notion", "github-intel"],
    "cmo": ["pinecone", "notion"],
    "coo": ["pinecone", "notion"],
    "cpo": ["pinecone", "notion"],
    "cro": ["pinecone", "notion", "sec-edgar", "pricing-calculator"],
}

# ── Role → KB Namespace Mapping ─────────────────────────────────────────────

ROLE_KB_NAMESPACES = {
    "ceo": ["lennys-podcast", "general-gtm", "market-analysis", "consulting"],
    "cfo": ["consulting", "revenue-architecture", "general-gtm"],
    "cto": ["ai-gtm", "lennys-podcast", "general-gtm"],
    "cmo": ["demand-gen", "lennys-podcast", "topline-podcast", "general-gtm"],
    "coo": ["consulting", "revenue-architecture", "general-gtm"],
    "cpo": ["lennys-podcast", "consulting", "general-gtm"],
    "cro": ["cro-school", "meddic", "topline-podcast", "revenue-architecture", "general-gtm"],
}
