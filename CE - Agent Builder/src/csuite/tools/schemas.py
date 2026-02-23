"""
Anthropic Tool Schemas for C-Suite Agent Function Calling.

Defines tool definitions in Anthropic's native format for wiring into
the `tools` parameter of messages.create(). Each schema maps to a
method on an existing tool client (SEC EDGAR, GitHub, Census, BLS, Pricing).

All tools are read-only.
"""

# =============================================================================
# SEC EDGAR Tools
# =============================================================================

SEC_SEARCH_COMPANIES = {
    "name": "sec_search_companies",
    "description": (
        "Search SEC EDGAR for public companies by name. Returns company info "
        "including CIK, ticker, SIC code, and state. Useful for finding public "
        "companies and their SEC identifiers."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Company name to search for (e.g., 'Accenture', 'Deloitte')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default 10)",
            },
        },
        "required": ["query"],
    },
}

SEC_GET_FINANCIALS = {
    "name": "sec_get_financials",
    "description": (
        "Get financial data for a public company from SEC XBRL filings. Returns "
        "revenue, net income, total assets, and employee count. Accepts a stock "
        "ticker (e.g., 'AAPL') or CIK number."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cik_or_ticker": {
                "type": "string",
                "description": "Stock ticker (e.g., 'AAPL') or SEC CIK number",
            },
        },
        "required": ["cik_or_ticker"],
    },
}

SEC_GET_FILINGS = {
    "name": "sec_get_filings",
    "description": (
        "Get recent SEC filings for a company. Returns filing type, date, and "
        "document info. Optionally filter by form type (10-K, 10-Q, 8-K, S-1, etc.)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cik_or_ticker": {
                "type": "string",
                "description": "Stock ticker or CIK number",
            },
            "form_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by form types (e.g., ['10-K', '10-Q']). Omit for all types.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of filings to return (default 10)",
            },
        },
        "required": ["cik_or_ticker"],
    },
}

SEC_GENERATE_PROSPECT_BRIEF = {
    "name": "sec_generate_prospect_brief",
    "description": (
        "Generate a comprehensive prospect research brief from SEC data. Aggregates "
        "company info, financials, recent filings, Form D (funding) data, and ICP "
        "fit analysis into a single structured output."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cik_or_ticker": {
                "type": "string",
                "description": "Stock ticker or CIK number",
            },
        },
        "required": ["cik_or_ticker"],
    },
}

# =============================================================================
# GitHub Tools
# =============================================================================

GITHUB_GET_ORG = {
    "name": "github_get_org",
    "description": (
        "Get GitHub organization info including public repos, members, followers, "
        "and description. Useful for assessing a prospect's engineering presence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "org_name": {
                "type": "string",
                "description": "GitHub organization login name (e.g., 'anthropics', 'stripe')",
            },
        },
        "required": ["org_name"],
    },
}

GITHUB_ANALYZE_TECH_STACK = {
    "name": "github_analyze_tech_stack",
    "description": (
        "Analyze a GitHub organization's tech stack from public repositories. Returns "
        "language breakdown, modern/legacy/AI language percentages, contributor count, "
        "and tech sophistication score (0-100)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "org_name": {
                "type": "string",
                "description": "GitHub organization login name",
            },
            "max_repos": {
                "type": "integer",
                "description": "Maximum repos to analyze (default 20, higher uses more API quota)",
            },
        },
        "required": ["org_name"],
    },
}

GITHUB_ASSESS_ENGINEERING_MATURITY = {
    "name": "github_assess_engineering_maturity",
    "description": (
        "Assess engineering maturity of a GitHub organization. Evaluates CI/CD, testing, "
        "documentation, security practices, and AI readiness. Returns maturity level "
        "(Advanced/Intermediate/Basic) with signals and opportunities."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "org_name": {
                "type": "string",
                "description": "GitHub organization login name",
            },
        },
        "required": ["org_name"],
    },
}

GITHUB_GENERATE_PROSPECT_PROFILE = {
    "name": "github_generate_prospect_profile",
    "description": (
        "Generate a complete technical profile for prospect research. Combines org info, "
        "tech stack analysis, activity metrics, and engineering maturity assessment with "
        "ICP fit signals."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "org_name": {
                "type": "string",
                "description": "GitHub organization login name",
            },
        },
        "required": ["org_name"],
    },
}

# =============================================================================
# Census Bureau Tools
# =============================================================================

CENSUS_ESTIMATE_MARKET_SIZE = {
    "name": "census_estimate_market_size",
    "description": (
        "Estimate total market size for an industry using Census Bureau data. Returns "
        "establishment count, employees, payroll, estimated revenue, and market "
        "concentration. Can scope to a specific state."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "naics_code": {
                "type": "string",
                "description": (
                    "6-digit NAICS industry code (e.g., '541512' for Computer Systems Design, "
                    "'541611' for Management Consulting)"
                ),
            },
            "state": {
                "type": "string",
                "description": "Optional state abbreviation (e.g., 'CA', 'NY') to limit geography",
            },
        },
        "required": ["naics_code"],
    },
}

CENSUS_GET_INDUSTRY_BENCHMARKS = {
    "name": "census_get_industry_benchmarks",
    "description": (
        "Get national industry benchmarks from Census Bureau. Returns establishment "
        "count, total employees, total payroll, average employees per firm, and "
        "average payroll per employee for a NAICS industry."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "naics_code": {
                "type": "string",
                "description": "6-digit NAICS industry code",
            },
        },
        "required": ["naics_code"],
    },
}

CENSUS_BENCHMARK_PROSPECT = {
    "name": "census_benchmark_prospect",
    "description": (
        "Benchmark a prospect company against industry averages. Compares employee "
        "count and revenue to Census data, determines ICP fit (20-150 employees), "
        "and generates sizing signals."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prospect_employees": {
                "type": "integer",
                "description": "Number of employees at the prospect company",
            },
            "naics_code": {
                "type": "string",
                "description": "Prospect's NAICS industry code",
            },
            "prospect_revenue": {
                "type": "number",
                "description": "Optional annual revenue figure in dollars",
            },
        },
        "required": ["prospect_employees", "naics_code"],
    },
}

# =============================================================================
# Bureau of Labor Statistics Tools
# =============================================================================

BLS_GET_EMPLOYMENT_TREND = {
    "name": "bls_get_employment_trend",
    "description": (
        "Get employment trend analysis for an industry. Compares recent vs prior "
        "period employment to determine if the industry is Expanding, Stable, or "
        "Contracting. Shows absolute and percentage change."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "naics_code": {
                "type": "string",
                "description": "6-digit NAICS industry code",
            },
            "months": {
                "type": "integer",
                "description": "Number of months to analyze (default 12)",
            },
        },
        "required": ["naics_code"],
    },
}

BLS_ASSESS_LABOR_MARKET = {
    "name": "bls_assess_labor_market",
    "description": (
        "Generate a labor market assessment for an industry. Combines employment "
        "trends, wage levels, and market tightness into an assessment with signals "
        "and consulting opportunities."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "naics_code": {
                "type": "string",
                "description": "6-digit NAICS industry code",
            },
        },
        "required": ["naics_code"],
    },
}

# =============================================================================
# Pricing Calculator Tools
# =============================================================================

PRICING_CALCULATE_AUDIT = {
    "name": "pricing_calculate_audit",
    "description": (
        "Calculate pricing for a Growth Strategy Audit engagement. Returns recommended "
        "price, margin analysis, floor/target/premium scenarios, ROI projection, and "
        "payment schedule. Base range: $15-25K."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "complexity": {
                "type": "string",
                "enum": ["standard", "complex", "enterprise"],
                "description": "Engagement complexity level (default: standard)",
            },
            "industry": {
                "type": "string",
                "enum": [
                    "professional_services", "technology", "healthcare",
                    "financial_services", "manufacturing", "other",
                ],
                "description": "Client industry vertical (default: professional_services)",
            },
            "timeline_weeks": {
                "type": "integer",
                "description": "Delivery timeline in weeks (default 3, rush < 2 adds premium)",
            },
            "client_revenue": {
                "type": "number",
                "description": "Client's annual revenue in dollars (for ROI calculation)",
            },
        },
        "required": [],
    },
}

PRICING_CALCULATE_IMPLEMENTATION = {
    "name": "pricing_calculate_implementation",
    "description": (
        "Calculate pricing for an Implementation Engagement. Returns recommended "
        "price with margin analysis and scenarios. Base range: $50-150K."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "complexity": {
                "type": "string",
                "enum": ["standard", "complex", "enterprise"],
                "description": "Engagement complexity level (default: complex)",
            },
            "industry": {
                "type": "string",
                "enum": [
                    "professional_services", "technology", "healthcare",
                    "financial_services", "manufacturing", "other",
                ],
                "description": "Client industry vertical",
            },
            "timeline_weeks": {
                "type": "integer",
                "description": "Delivery timeline in weeks (default 12)",
            },
            "scope_description": {
                "type": "string",
                "description": "Brief description of implementation scope",
            },
            "client_revenue": {
                "type": "number",
                "description": "Client's annual revenue in dollars",
            },
        },
        "required": [],
    },
}

PRICING_CALCULATE_RETAINER = {
    "name": "pricing_calculate_retainer",
    "description": (
        "Calculate pricing for a Retainer engagement. Returns monthly rate with "
        "commitment discounts (5% for 3mo, 10% for 6mo, 15% for 12mo). "
        "Base range: $10-25K/month."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "complexity": {
                "type": "string",
                "enum": ["standard", "complex", "enterprise"],
                "description": "Engagement complexity level",
            },
            "commitment_months": {
                "type": "integer",
                "description": "Commitment term length: 1, 3, 6, or 12 months",
            },
            "hours_per_month": {
                "type": "integer",
                "description": "Expected advisory hours per month (default 10)",
            },
            "client_revenue": {
                "type": "number",
                "description": "Client's annual revenue in dollars",
            },
        },
        "required": [],
    },
}

# =============================================================================
# Pinecone Knowledge Base Tools
# =============================================================================

PINECONE_SEARCH_KNOWLEDGE = {
    "name": "pinecone_search_knowledge",
    "description": (
        "Search the Cardinal Element GTM knowledge base for relevant frameworks, "
        "strategies, and insights. Contains curated content on revenue architecture, "
        "demand generation, leadership, MEDDIC sales methodology, consulting, "
        "forecasting, and more. Use this to ground advice in proven frameworks."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing the knowledge needed",
            },
            "namespace": {
                "type": "string",
                "description": (
                    "Optional: specific namespace to search. "
                    "If omitted, searches role-appropriate namespaces."
                ),
                "enum": [
                    "ai-gtm", "lennys-podcast", "leadership", "cmo-school",
                    "demand-gen", "cro-school", "cco-school", "meddic",
                    "forecasting", "consulting", "revenue-architecture",
                    "finance-leadership", "general-gtm", "market-analysis",
                ],
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results (default 5, max 10)",
            },
        },
        "required": ["query"],
    },
}

# =============================================================================
# Image Generation Tools
# =============================================================================

OPENAI_GENERATE_IMAGE = {
    "name": "openai_generate_image",
    "description": (
        "Generate an image using OpenAI GPT Image 1. Creates marketing visuals, "
        "social media graphics, campaign imagery, or product concept art. Returns "
        "the local file path of the saved image."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Detailed image generation prompt. Include style, mood, colors, "
                    "composition, and intended use for best results."
                ),
            },
            "size": {
                "type": "string",
                "enum": ["1024x1024", "1536x1024", "1024x1536", "auto"],
                "description": (
                    "Image dimensions. 1024x1024 (square), 1536x1024 (landscape), "
                    "1024x1536 (portrait), auto (model chooses). Default: auto."
                ),
            },
            "quality": {
                "type": "string",
                "enum": ["low", "medium", "high", "auto"],
                "description": "Image quality level. Higher = more detail + cost. Default: medium.",
            },
            "style": {
                "type": "string",
                "enum": ["vivid", "natural"],
                "description": "vivid = hyper-real/dramatic, natural = more realistic. Optional.",
            },
        },
        "required": ["prompt"],
    },
}

GEMINI_GENERATE_IMAGE = {
    "name": "gemini_generate_image",
    "description": (
        "Generate an image using Gemini 3 Pro (image preview). Creates marketing visuals, "
        "product mockups, or creative artwork. Returns the local file path of the "
        "saved image."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Detailed image generation prompt. Include style, mood, colors, "
                    "composition, and intended use for best results."
                ),
            },
            "size": {
                "type": "string",
                "enum": ["1024x1024", "1536x1024", "1024x1536"],
                "description": (
                    "Image dimensions. 1024x1024 (square), 1536x1024 (landscape), "
                    "1024x1536 (portrait). Default: 1024x1024."
                ),
            },
        },
        "required": ["prompt"],
    },
}

# =============================================================================
# Web Search Tools
# =============================================================================

WEB_SEARCH = {
    "name": "web_search",
    "description": (
        "Search the web for current industry data, competitor info, benchmarks, "
        "and trends using Brave Search. Returns titles, URLs, and descriptions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'AI consulting market size 2026')",
            },
            "count": {
                "type": "integer",
                "description": "Number of results to return (1-20, default 5)",
            },
        },
        "required": ["query"],
    },
}

WEB_FETCH = {
    "name": "web_fetch",
    "description": (
        "Retrieve and read content from a specific web page. Extracts visible "
        "text from HTML pages. Useful for reading articles, reports, and documentation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL to fetch (e.g., 'https://example.com/article')",
            },
        },
        "required": ["url"],
    },
}

# =============================================================================
# Notion Tools
# =============================================================================

NOTION_SEARCH = {
    "name": "notion_search",
    "description": (
        "Search the Notion workspace for pages and databases by keyword. "
        "Returns matching page/database titles, IDs, and URLs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for Notion workspace",
            },
            "filter_type": {
                "type": "string",
                "enum": ["page", "database"],
                "description": "Optional: filter results to only pages or only databases",
            },
        },
        "required": ["query"],
    },
}

NOTION_QUERY_DATABASE = {
    "name": "notion_query_database",
    "description": (
        "Query a Notion database to retrieve rows/entries. Supports filtering "
        "and sorting. Returns flattened property values for each row."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "database_id": {
                "type": "string",
                "description": "The Notion database ID to query",
            },
            "filter": {
                "type": "object",
                "description": "Optional Notion filter object (see Notion API docs)",
            },
            "sorts": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Optional list of sort objects",
            },
        },
        "required": ["database_id"],
    },
}

NOTION_CREATE_PAGE = {
    "name": "notion_create_page",
    "description": (
        "Create a new page in Notion under a database or page. Supports markdown "
        "content that gets converted to Notion blocks (headings, paragraphs, bullets)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "parent_id": {
                "type": "string",
                "description": "Database ID or page ID for the parent",
            },
            "title": {
                "type": "string",
                "description": "Page title",
            },
            "content": {
                "type": "string",
                "description": "Optional markdown content for the page body",
            },
            "properties": {
                "type": "object",
                "description": "Optional additional database properties (key-value pairs)",
            },
        },
        "required": ["parent_id", "title"],
    },
}

# =============================================================================
# File Export Tools
# =============================================================================

WRITE_DELIVERABLE = {
    "name": "write_deliverable",
    "description": (
        "Save a deliverable as a markdown file. Validates naming convention "
        "({EXEC}-D{N}-{ShortName}.md) and creates directories as needed. "
        "Files are saved under reports/{directory}/."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Filename (e.g., 'CMO-D6-LinkedIn-Post-4.md')",
            },
            "content": {
                "type": "string",
                "description": "Markdown content to save",
            },
            "directory": {
                "type": "string",
                "description": "Subdirectory under reports/ (default: 'deliverables')",
            },
        },
        "required": ["filename", "content"],
    },
}

EXPORT_PDF = {
    "name": "export_pdf",
    "description": (
        "Export a markdown file to PDF with Cardinal Element branding. "
        "Saves the PDF alongside the source markdown file."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "markdown_path": {
                "type": "string",
                "description": "Path to the markdown file to convert to PDF",
            },
        },
        "required": ["markdown_path"],
    },
}

# =============================================================================
# QA Validation Tools
# =============================================================================

QA_VALIDATE = {
    "name": "qa_validate",
    "description": (
        "Run 3-tier quality assurance validation on deliverable content. "
        "Tier 1: format/completeness (Haiku). Tier 2: accuracy/methodology (Sonnet). "
        "Tier 3: strategic alignment (Opus). Returns pass/fail with scores and issues."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The deliverable content to validate",
            },
            "tier": {
                "type": "string",
                "enum": ["1", "2", "3", "all"],
                "description": "Which tier to run: '1', '2', '3', or 'all' (default: 'all')",
            },
            "context": {
                "type": "string",
                "description": "Optional context (deliverable name, target audience, etc.)",
            },
        },
        "required": ["content"],
    },
}

# =============================================================================
# All Schemas (for import convenience)
# =============================================================================

ALL_TOOL_SCHEMAS = {
    "sec_search_companies": SEC_SEARCH_COMPANIES,
    "sec_get_financials": SEC_GET_FINANCIALS,
    "sec_get_filings": SEC_GET_FILINGS,
    "sec_generate_prospect_brief": SEC_GENERATE_PROSPECT_BRIEF,
    "github_get_org": GITHUB_GET_ORG,
    "github_analyze_tech_stack": GITHUB_ANALYZE_TECH_STACK,
    "github_assess_engineering_maturity": GITHUB_ASSESS_ENGINEERING_MATURITY,
    "github_generate_prospect_profile": GITHUB_GENERATE_PROSPECT_PROFILE,
    "census_estimate_market_size": CENSUS_ESTIMATE_MARKET_SIZE,
    "census_get_industry_benchmarks": CENSUS_GET_INDUSTRY_BENCHMARKS,
    "census_benchmark_prospect": CENSUS_BENCHMARK_PROSPECT,
    "bls_get_employment_trend": BLS_GET_EMPLOYMENT_TREND,
    "bls_assess_labor_market": BLS_ASSESS_LABOR_MARKET,
    "pricing_calculate_audit": PRICING_CALCULATE_AUDIT,
    "pricing_calculate_implementation": PRICING_CALCULATE_IMPLEMENTATION,
    "pricing_calculate_retainer": PRICING_CALCULATE_RETAINER,
    "pinecone_search_knowledge": PINECONE_SEARCH_KNOWLEDGE,
    "openai_generate_image": OPENAI_GENERATE_IMAGE,
    "gemini_generate_image": GEMINI_GENERATE_IMAGE,
    "web_search": WEB_SEARCH,
    "web_fetch": WEB_FETCH,
    "notion_search": NOTION_SEARCH,
    "notion_query_database": NOTION_QUERY_DATABASE,
    "notion_create_page": NOTION_CREATE_PAGE,
    "write_deliverable": WRITE_DELIVERABLE,
    "export_pdf": EXPORT_PDF,
    "qa_validate": QA_VALIDATE,
}
