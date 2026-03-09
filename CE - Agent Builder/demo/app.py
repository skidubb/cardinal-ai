"""
Streamlit Demo: Cardinal Element Prospect Research and AI Advisory

A single-file demo that showcases Cardinal Element's AI-powered prospect research
and C-Suite advisory capabilities. Three modes:

1. **Discover ICP Prospects** -- Proactively surfaces B2B operators matching CE's ICP
   by searching SEC EDGAR, filtering by SIC code, and scoring against ICP criteria.
2. **Research a Company** -- Accepts a ticker or name, runs SEC EDGAR enrichment,
   displays a prospect brief with ICP fit scoring, and shows a C-Suite agent response.
3. **ODSC Demo** -- Pre-loaded walkthrough with cached data for conference presentations.
   No live API dependency. Includes presentation mode toggle for larger fonts.

Deployed to Streamlit Community Cloud for live demonstrations during discovery calls.

CTO Sprint 2 Deliverables:
- D1: Streamlit Demo Deployment (public URL)
- D5: ODSC Demo Environment (pre-cached data, presentation mode)

Tech Debt (Named for Sprint 3 paydown):
- Single-file architecture (replace with Next.js/FastAPI in Sprint 3)
- Hardcoded styling and layout
- No authentication or session persistence
- Graceful degradation for API failures (shows partial results)
"""

import asyncio
import os
from typing import Any

import pandas as pd
import streamlit as st
from ce_shared.env import find_and_load_dotenv

from csuite.agents.cfo import CFOAgent
from csuite.agents.cmo import CMOAgent
from csuite.agents.coo import COOAgent
from csuite.agents.cto import CTOAgent
from csuite.config import AgentConfig, get_settings
from csuite.tools.report_generator import ProspectReportGenerator
from csuite.tools.sec_edgar import (
    CompanyInfo,
    ProspectResearchBrief,
    SECEdgarClient,
)

# Import pre-cached demo data (CTO D5: ODSC Demo Environment)
from demo_data import (
    DEMO_COMPANIES,
    get_demo_company,
    get_demo_response,
    list_demo_companies,
)

# Load environment variables from monorepo root .env
find_and_load_dotenv(project="agent-builder")

# ============================================================================
# Constants
# ============================================================================

ICP_SEARCH_QUERIES = {
    "Management Consulting": "management consulting services",
    "Engineering Services": "engineering services",
    "Professional Services": "professional services",
    "Staffing & HR": "staffing services",
    "Marketing & Advertising": "marketing agency",
    "Accounting & Tax": "accounting services",
}

B2B_SIC_KEYWORDS = [
    "consulting", "services", "engineering", "management",
    "professional", "technical", "staffing", "accounting",
    "advertising", "public relations", "marketing",
]

NON_ICP_SIC_KEYWORDS = [
    "investment", "bank", "insurance", "real estate investment",
    "oil", "gas", "mining", "pharmaceutical", "retail",
]

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Cardinal Element -- Prospect Research Demo",
    page_icon="CE",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================================
# Presentation Mode (CTO D5: ODSC Demo Environment)
# ============================================================================

def get_presentation_css() -> str:
    """Return CSS for presentation mode with larger fonts."""
    return """
    /* Presentation mode overrides */
    .stMarkdown p, .stMarkdown li {
        font-size: 1.3em !important;
        line-height: 1.6 !important;
    }

    .stMarkdown h1 { font-size: 3em !important; }
    .stMarkdown h2 { font-size: 2.4em !important; }
    .stMarkdown h3 { font-size: 1.8em !important; }

    .ce-header h1 { font-size: 3.5em !important; }
    .ce-header p { font-size: 1.5em !important; }

    .metric-value { font-size: 2.4em !important; }
    .metric-label { font-size: 1.1em !important; }

    .ce-section { padding: 30px !important; }
    .ce-section p, .ce-section li {
        font-size: 1.3em !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.4em !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 1.1em !important;
    }
    """


# Check presentation mode from sidebar (renders later)
if "presentation_mode" not in st.session_state:
    st.session_state.presentation_mode = False

presentation_mode = st.session_state.presentation_mode

# Base CSS
base_css = """
    /* Cardinal Element brand colors */
    :root {
        --ce-navy: #0B1E3F;
        --ce-gold: #D4AF37;
        --ce-light: #F5F5F5;
    }

    /* Header styling */
    .ce-header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 2px solid #E0E0E0;
        margin-bottom: 30px;
    }

    .ce-header h1 {
        margin: 0;
        color: #0B1E3F;
        font-size: 2.5em;
        font-weight: 700;
    }

    .ce-header p {
        margin: 5px 0 0 0;
        color: #666;
        font-size: 1.1em;
    }

    /* Section styling */
    .ce-section {
        background: #F9F9F9;
        border-left: 4px solid #D4AF37;
        padding: 20px;
        margin: 20px 0;
        border-radius: 4px;
    }

    .ce-section h2 {
        margin-top: 0;
        color: #0B1E3F;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #E0E0E0;
        border-radius: 4px;
        padding: 15px;
        margin: 10px 0;
    }

    .metric-label {
        font-size: 0.85em;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }

    .metric-value {
        font-size: 1.8em;
        font-weight: 700;
        color: #0B1E3F;
    }

    /* ICP Fit visual */
    .icp-fit-excellent { color: #10B981; font-weight: 700; }
    .icp-fit-good { color: #3B82F6; font-weight: 700; }
    .icp-fit-fair { color: #F59E0B; font-weight: 700; }
    .icp-fit-poor { color: #EF4444; font-weight: 700; }

    /* Error and status messages */
    .ce-error {
        background: #FEE2E2;
        border-left: 4px solid #EF4444;
        padding: 15px;
        border-radius: 4px;
        margin: 15px 0;
    }

    .ce-success {
        background: #ECFDF5;
        border-left: 4px solid #10B981;
        padding: 15px;
        border-radius: 4px;
        margin: 15px 0;
    }

    /* Degraded data notice */
    .ce-degraded {
        background: #FFF7ED;
        border-left: 4px solid #F59E0B;
        padding: 12px;
        border-radius: 4px;
        margin: 10px 0;
        font-size: 0.9em;
    }
"""

presentation_css = get_presentation_css() if presentation_mode else ""

st.markdown(f"<style>{base_css}{presentation_css}</style>", unsafe_allow_html=True)


# ============================================================================
# Helper Functions
# ============================================================================


def format_currency(value: float | None) -> str:
    """Format a number as currency."""
    if value is None:
        return "N/A"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.0f}"


def get_icp_fit_class(score: float) -> str:
    """Return CSS class for ICP fit score."""
    if score >= 0.8:
        return "icp-fit-excellent"
    if score >= 0.6:
        return "icp-fit-good"
    if score >= 0.4:
        return "icp-fit-fair"
    return "icp-fit-poor"


def get_icp_fit_label(score: float) -> str:
    """Return label for ICP fit score."""
    if score >= 0.8:
        return "EXCELLENT FIT"
    if score >= 0.6:
        return "GOOD FIT"
    if score >= 0.4:
        return "FAIR FIT"
    return "POOR FIT"


def filter_by_sic(submissions: dict[str, Any]) -> bool:
    """Check if a company's SIC description indicates a B2B operator."""
    sic_desc = submissions.get("sicDescription", "")
    if not sic_desc:
        return False
    sic_lower = sic_desc.lower()
    if any(kw in sic_lower for kw in NON_ICP_SIC_KEYWORDS):
        return False
    return any(kw in sic_lower for kw in B2B_SIC_KEYWORDS)


async def discover_prospects(
    selected_industries: list[str],
    progress_bar: Any,
    status_text: Any,
) -> list[dict[str, Any]]:
    """Run the three-stage ICP discovery pipeline."""
    client = SECEdgarClient()
    sem = asyncio.Semaphore(5)

    status_text.text("Stage 1/3: Searching SEC EDGAR for B2B companies...")
    all_companies: list[CompanyInfo] = []
    seen_ciks: set[str] = set()

    for i, industry in enumerate(selected_industries):
        query = ICP_SEARCH_QUERIES[industry]
        try:
            results = await client.search_companies(query, limit=10)
        except Exception:
            continue
        for company in results:
            if company.cik and company.cik not in seen_ciks:
                seen_ciks.add(company.cik)
                all_companies.append(company)
        progress_bar.progress(
            int((i + 1) / len(selected_industries) * 25),
            text=f"Searched {i + 1}/{len(selected_industries)} industries "
                 f"({len(all_companies)} unique companies)...",
        )

    if not all_companies:
        status_text.text("No companies found. Try different industries.")
        progress_bar.progress(100)
        return []

    status_text.text(
        f"Stage 2/3: Enriching {len(all_companies)} companies "
        f"(filtering to B2B operators)..."
    )

    async def enrich_one(company: CompanyInfo) -> CompanyInfo | None:
        async with sem:
            try:
                submissions = await client.get_company_submissions(company.cik)
            except Exception:
                return None
            if not submissions or not filter_by_sic(submissions):
                return None
            tickers = submissions.get("tickers", [])
            return CompanyInfo(
                cik=company.cik,
                name=submissions.get("name", company.name),
                ticker=tickers[0] if tickers else None,
                sic=submissions.get("sic"),
                sic_description=submissions.get("sicDescription"),
                state=submissions.get("stateOfIncorporation"),
                entity_type=submissions.get("entityType"),
            )

    enrich_results = await asyncio.gather(
        *[enrich_one(c) for c in all_companies],
        return_exceptions=True,
    )
    enriched = [r for r in enrich_results if isinstance(r, CompanyInfo)]
    progress_bar.progress(
        60, text=f"Found {len(enriched)} B2B companies from {len(all_companies)} total"
    )

    if not enriched:
        status_text.text("No B2B companies matched the SIC filter.")
        progress_bar.progress(100)
        return []

    status_text.text(f"Stage 3/3: Scoring {len(enriched)} B2B prospects...")

    async def score_one(company_info: CompanyInfo) -> dict[str, Any] | None:
        async with sem:
            try:
                financials = await client.get_company_financials(company_info.cik)
            except Exception:
                financials = None
            brief = ProspectResearchBrief(
                company_info=company_info,
                financials=financials,
            )
            icp_fit = client._calculate_icp_fit(brief)
            return {
                "company_info": company_info,
                "financials": financials,
                "icp_fit": icp_fit,
            }

    score_results = await asyncio.gather(
        *[score_one(c) for c in enriched],
        return_exceptions=True,
    )
    prospects = [r for r in score_results if isinstance(r, dict)]
    progress_bar.progress(100, text="Discovery complete!")
    prospects.sort(key=lambda x: x["icp_fit"]["overall_score"], reverse=True)
    return prospects


async def fetch_prospect_data(ticker_or_name: str) -> dict[str, Any]:
    """Fetch prospect data from SEC EDGAR, with pre-cached data fallback."""
    # Check pre-cached demo data first (CTO D5)
    demo = get_demo_company(ticker_or_name)
    if demo:
        icp_fit = calculate_icp_fit(demo["company_info"], demo["financials"])
        return {
            "company_info": demo["company_info"],
            "financials": demo["financials"],
            "icp_fit": icp_fit,
            "error": None,
            "cached": True,
        }

    client = SECEdgarClient()

    try:
        company_info = await client.get_company_info(ticker_or_name)
        if not company_info:
            return {"error": f"Company not found: {ticker_or_name}"}

        financials = await client.get_company_financials(company_info.cik)
        icp_fit = calculate_icp_fit(company_info, financials)

        return {
            "company_info": company_info,
            "financials": financials,
            "icp_fit": icp_fit,
            "error": None,
            "cached": False,
        }
    except Exception as e:
        return {
            "error": f"Error fetching data: {str(e)}",
            "company_info": None,
            "financials": None,
        }


def calculate_icp_fit(company_info: Any, financials: Any) -> dict[str, Any]:
    """Calculate ICP fit score based on company profile."""
    score = 0.0
    reasons = []

    if company_info and financials:
        if financials.revenue:
            if 5_000_000 <= financials.revenue <= 40_000_000:
                score += 0.4
                reasons.append(f"Revenue ${financials.revenue:,.0f} is in target range")
            elif 2_000_000 <= financials.revenue < 5_000_000:
                score += 0.2
                reasons.append("Revenue is below target range")
            elif 40_000_000 < financials.revenue <= 100_000_000:
                score += 0.2
                reasons.append("Revenue is above target range")
            else:
                reasons.append("Revenue outside target range")

        if company_info.sic_description:
            sic_lower = company_info.sic_description.lower()
            b2b_indicators = [
                "software", "consulting", "services", "professional",
                "business", "manufacturing", "logistics", "distribution"
            ]
            if any(ind in sic_lower for ind in b2b_indicators):
                score += 0.3
                reasons.append(f"Industry aligned: {company_info.sic_description}")
            else:
                score += 0.1

    icp_fit_score = min(score, 1.0)

    return {
        "overall_score": icp_fit_score,
        "fit_label": get_icp_fit_label(icp_fit_score),
        "fit_class": get_icp_fit_class(icp_fit_score),
        "reasons": reasons,
    }


DEMO_AGENT_MAP: dict[str, type] = {
    "CFO": CFOAgent,
    "CTO": CTOAgent,
    "CMO": CMOAgent,
    "COO": COOAgent,
}


async def query_agent(agent_class: type, question: str) -> str:
    """Query a C-Suite agent for a response using Sonnet for demo speed."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    demo_config = AgentConfig(
        name=f"Demo {agent_class.ROLE.upper()}",
        role=agent_class.ROLE,
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.6,
    )
    agent = agent_class(config=demo_config)
    return await agent.chat(question)


# ============================================================================
# Render: Company Results (shared between Research tab and ODSC tab)
# ============================================================================

def render_company_results(
    company_info: Any,
    financials: Any,
    icp_fit: dict,
    show_agent_query: bool = True,
    is_cached: bool = False,
    ticker_for_demo: str | None = None,
) -> None:
    """Render company overview, financials, ICP fit, and agent query section."""

    if is_cached:
        st.markdown(
            '<div class="ce-degraded">'
            '<strong>Pre-cached data</strong> -- loaded instantly for demo reliability.'
            '</div>',
            unsafe_allow_html=True,
        )

    # Company Overview
    st.markdown("### Company Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        name_display = (company_info.name[:20] + "..."
                        if len(company_info.name) > 20 else company_info.name)
        st.metric("Company", name_display)
    with col2:
        st.metric("Ticker", company_info.ticker or "N/A")
    with col3:
        st.metric("State", company_info.state or "N/A")
    with col4:
        industry = company_info.sic_description or "N/A"
        st.metric("Industry", industry[:15] + "..." if len(industry) > 15 else industry)

    # Financial Metrics
    if financials:
        st.markdown("### Financial Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Annual Revenue", format_currency(financials.revenue))
        with col2:
            st.metric("Net Income", format_currency(financials.net_income))
        with col3:
            employees = financials.employees or "N/A"
            if isinstance(employees, int):
                st.metric("Employees", f"{employees:,}")
            else:
                st.metric("Employees", employees)

    # ICP Fit Analysis
    st.markdown("### ICP Fit Analysis")
    icp_score = icp_fit["overall_score"]
    icp_class = icp_fit["fit_class"]
    icp_label = icp_fit["fit_label"]

    col1, col2 = st.columns([1, 2])
    with col1:
        if icp_score >= 0.8:
            indicator = "HIGH"
        elif icp_score >= 0.6:
            indicator = "MED"
        else:
            indicator = "LOW"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Cardinal Element ICP Fit</div>
                <div class="metric-value">
                    <span class="{icp_class}">{icp_label}</span>
                </div>
                <div style="margin-top: 10px; font-size: 1.5em; font-weight: 700;">
                    [{indicator}]
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown("**ICP Profile:** B2B Operators, $5M-$40M ARR, 20-150 employees")
        if icp_fit["reasons"]:
            st.markdown("**Analysis:**")
            for reason in icp_fit["reasons"]:
                st.markdown(f"- {reason}")

    # Download button for prospect brief
    generator = ProspectReportGenerator()
    download_content = generator.generate_markdown(company_info, financials, icp_fit)
    company_slug = (company_info.ticker or company_info.name[:10]).replace(" ", "_")
    st.download_button(
        label="Download Prospect Brief (Markdown)",
        data=download_content,
        file_name=f"prospect_brief_{company_slug}.md",
        mime="text/markdown",
    )

    if not show_agent_query:
        return

    # C-Suite Agent Query
    st.markdown("---")
    st.markdown("### Ask a C-Suite Advisor")

    agent_col, question_col = st.columns([1, 3])
    with agent_col:
        agent_choice = st.selectbox(
            "Select Agent",
            list(DEMO_AGENT_MAP.keys()),
            label_visibility="collapsed",
            key=f"agent_select_{ticker_for_demo or 'research'}",
        )
    with question_col:
        agent_question = st.text_input(
            "Question",
            placeholder="e.g., What are the key risks for this prospect?",
            label_visibility="collapsed",
            key=f"agent_question_{ticker_for_demo or 'research'}",
        )

    if st.button(
        "Get Recommendation",
        use_container_width=False,
        key=f"agent_btn_{ticker_for_demo or 'research'}",
    ):
        if not agent_question:
            st.warning("Please enter a question")
        else:
            # Check for pre-cached agent response first (CTO D5)
            if ticker_for_demo:
                cached_response = get_demo_response(ticker_for_demo, agent_choice)
                if cached_response:
                    st.markdown(cached_response)
                    st.caption("Pre-cached response -- loaded instantly for demo reliability.")
                    return

            with st.spinner(f"Getting {agent_choice} perspective..."):
                company_context = f"""
Company: {company_info.name}
Ticker: {company_info.ticker or 'N/A'}
Industry: {company_info.sic_description or 'N/A'}
Annual Revenue: {format_currency(financials.revenue if financials else None)}
State: {company_info.state or 'N/A'}
ICP Fit Score: {icp_label}

Question: {agent_question}
"""
                try:
                    agent_class = DEMO_AGENT_MAP[agent_choice]
                    response = asyncio.run(query_agent(agent_class, company_context))
                    st.markdown(response)
                except Exception as e:
                    st.error(f"Agent query failed: {e}")
                    if os.environ.get("CE_DEBUG"):
                        st.exception(e)


# ============================================================================
# Page Layout
# ============================================================================

# Header
st.markdown(
    """
    <div class="ce-header">
        <h1>Cardinal Element</h1>
        <p>AI-Powered Prospect Research & C-Suite Advisory</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# Tabs (3 tabs: Discover, Research, ODSC Demo)
# ============================================================================

tab_discover, tab_research, tab_odsc = st.tabs([
    "Discover ICP Prospects",
    "Research a Company",
    "ODSC Demo",
])

# ============================================================================
# Tab 1: Discover ICP Prospects
# ============================================================================

with tab_discover:
    st.markdown(
        """
        Discover public companies matching Cardinal Element's ICP:
        **B2B operators, $5M-$40M revenue, 20-150 employees**.
        Select industries to search, then click Discover.
        """
    )

    selected_industries = st.multiselect(
        "Industries to search",
        options=list(ICP_SEARCH_QUERIES.keys()),
        default=list(ICP_SEARCH_QUERIES.keys()),
    )

    col_discover, col_refresh = st.columns([1, 4])
    with col_discover:
        discover_clicked = st.button(
            "Discover Prospects",
            use_container_width=True,
            disabled=len(selected_industries) == 0,
        )
    with col_refresh:
        refresh_clicked = st.button("Refresh Results")

    if (discover_clicked or refresh_clicked) and selected_industries:
        progress_bar = st.progress(0, text="Starting discovery...")
        status_text = st.empty()

        try:
            results = asyncio.run(
                discover_prospects(selected_industries, progress_bar, status_text)
            )
            st.session_state.discovery_results = results
            st.session_state.discovery_industries = selected_industries
            status_text.text(
                f"Found {len(results)} prospects across "
                f"{len(selected_industries)} industries."
            )
        except Exception as e:
            st.error(f"Discovery failed: {e}")
            if os.environ.get("CE_DEBUG"):
                st.exception(e)

    if "discovery_results" in st.session_state and st.session_state.discovery_results:
        results = st.session_state.discovery_results

        st.markdown(f"### {len(results)} Prospects Found")

        df_rows = []
        for r in results:
            ci = r["company_info"]
            fi = r["financials"]
            icp = r["icp_fit"]
            score = icp.get("overall_score", 0)

            if score >= 70:
                fit_label = "Excellent"
            elif score >= 50:
                fit_label = "Good"
            elif score >= 30:
                fit_label = "Fair"
            else:
                fit_label = "Low"

            df_rows.append({
                "Company": ci.name,
                "Ticker": ci.ticker or "--",
                "Industry": ci.sic_description or "--",
                "Revenue": fi.revenue if fi else None,
                "Employees": fi.employees if fi else None,
                "ICP Score": score,
                "Fit": fit_label,
                "State": ci.state or "--",
            })

        df = pd.DataFrame(df_rows)

        st.dataframe(
            df,
            column_config={
                "Company": st.column_config.TextColumn("Company", width="large"),
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Industry": st.column_config.TextColumn("Industry", width="medium"),
                "Revenue": st.column_config.NumberColumn(
                    "Revenue", format="$%.0f", width="small",
                ),
                "Employees": st.column_config.NumberColumn(
                    "Employees", format="%d", width="small",
                ),
                "ICP Score": st.column_config.ProgressColumn(
                    "ICP Score", min_value=0, max_value=100, width="small",
                ),
                "Fit": st.column_config.TextColumn("Fit", width="small"),
                "State": st.column_config.TextColumn("State", width="small"),
            },
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.markdown("#### Research a Prospect")

        company_names = [r["company_info"].name for r in results]
        selected_prospect = st.selectbox(
            "Select a prospect to research",
            options=company_names,
            key="prospect_selector",
        )

        if st.button("View Details", key="view_details_btn"):
            idx = company_names.index(selected_prospect)
            result = results[idx]
            ci = result["company_info"]
            fi = result["financials"]

            icp_fit = calculate_icp_fit(ci, fi)
            st.session_state.prospect_data = {
                "company_info": ci,
                "financials": fi,
                "icp_fit": icp_fit,
                "error": None,
            }
            st.session_state.company_input = ci.name
            st.rerun()

    elif "discovery_results" in st.session_state:
        st.info("No prospects matched the selected industries. Try broader criteria.")

# ============================================================================
# Tab 2: Research a Company
# ============================================================================

with tab_research:
    st.markdown(
        """
        **Search for a public company** to see how Cardinal Element's AI agents analyze
        prospects and provide strategic recommendations. Enter a stock ticker (e.g., AAPL,
        MSFT) or company name to get started.
        """
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        company_input = st.text_input(
            "Company Ticker or Name",
            placeholder="e.g., AAPL or Apple Inc",
            label_visibility="collapsed",
            key="research_input",
        )

    with col2:
        search_button = st.button("Search", use_container_width=True, key="research_search")

    if search_button and company_input:
        with st.spinner("Searching for company..."):
            prospect_data = asyncio.run(fetch_prospect_data(company_input))

            if prospect_data.get("error"):
                st.markdown(
                    f'<div class="ce-error">'
                    f'<strong>Error:</strong> {prospect_data["error"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.session_state.pop("prospect_data", None)
            else:
                st.session_state.prospect_data = prospect_data
                st.session_state.company_input = company_input

    if "prospect_data" in st.session_state:
        prospect_data = st.session_state.prospect_data
        render_company_results(
            company_info=prospect_data["company_info"],
            financials=prospect_data["financials"],
            icp_fit=prospect_data["icp_fit"],
            show_agent_query=True,
            is_cached=prospect_data.get("cached", False),
        )

        st.markdown("---")
        st.markdown(
            """
            **About Cardinal Element:** AI-native growth architecture consultancy.
            We replace executive advisory layers with AI agents optimized for
            B2B operators.

            *This is a demo environment. All data sourced from SEC EDGAR
            public filings.*
            """
        )

# ============================================================================
# Tab 3: ODSC Demo (CTO D5: ODSC Demo Environment)
# ============================================================================

with tab_odsc:
    st.markdown(
        """
        ### ODSC AI East 2026 -- Live Demo

        **Talk:** How We Replaced an Executive Team with AI Agents

        This demo walks through Cardinal Element's AI-powered prospect research
        pipeline using pre-cached data. No live API dependency -- works offline.

        Select a company below to see the full analysis.
        """
    )

    # Company selector
    demo_companies = list_demo_companies()
    demo_labels = [f"{c['ticker']} -- {c['name']}" for c in demo_companies]

    selected_demo = st.selectbox(
        "Select a demo company",
        options=range(len(demo_labels)),
        format_func=lambda i: demo_labels[i],
        key="odsc_company_select",
    )

    demo_company = demo_companies[selected_demo]
    st.info(demo_company["narrative"])

    # Load and render
    demo_data = get_demo_company(demo_company["ticker"])
    if demo_data:
        icp_fit = calculate_icp_fit(
            demo_data["company_info"],
            demo_data["financials"],
        )

        render_company_results(
            company_info=demo_data["company_info"],
            financials=demo_data["financials"],
            icp_fit=icp_fit,
            show_agent_query=True,
            is_cached=True,
            ticker_for_demo=demo_company["ticker"],
        )

    # Architecture diagram
    st.markdown("---")
    st.markdown("### System Architecture")
    st.markdown(
        """
        ```mermaid
        graph TB
            subgraph "Client Layer"
                UI[Streamlit Demo App]
                CLI[CLI: csuite command]
            end

            subgraph "Agent Layer"
                CFO[CFO Agent]
                CTO[CTO Agent]
                CMO[CMO Agent]
                COO[COO Agent]
                ORCH[Orchestrator<br/>Parallel Query + Synthesis]
            end

            subgraph "Data Layer"
                SEC[SEC EDGAR API<br/>Company Financials]
                CENSUS[Census Bureau API<br/>Industry Benchmarks]
                BLS[BLS API<br/>Labor Market Data]
                GH[GitHub API<br/>Tech Stack Analysis]
            end

            subgraph "Intelligence Layer"
                CLAUDE[Claude API<br/>Opus / Sonnet / Haiku]
                ICP[ICP Scoring Engine]
                COST[Cost Tracker<br/>D10 Compliance]
            end

            UI --> ORCH
            CLI --> ORCH
            ORCH --> CFO & CTO & CMO & COO
            CFO & CTO & CMO & COO --> CLAUDE
            UI --> SEC & GH
            UI --> ICP
            ORCH --> COST

            style UI fill:#D4AF37,color:#0B1E3F,stroke:#0B1E3F
            style CLAUDE fill:#0B1E3F,color:#fff,stroke:#D4AF37
            style ICP fill:#10B981,color:#fff,stroke:#0B1E3F
        ```

        **Key Design Decisions:**
        - All agents use Claude Opus for strategic reasoning
        - Demo uses Sonnet for faster response times
        - 4 free government APIs replace $500+/mo in paid data services
        - ICP scoring is deterministic (no LLM in the loop)
        - Cost tracking on every API call (Directive D10)
        """
    )

# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.markdown("### Settings")

    # Presentation mode toggle (CTO D5)
    pres_mode = st.toggle(
        "Presentation Mode",
        value=st.session_state.presentation_mode,
        help="Larger fonts for conference presentations",
        key="pres_mode_toggle",
    )
    if pres_mode != st.session_state.presentation_mode:
        st.session_state.presentation_mode = pres_mode
        st.rerun()

    st.markdown("---")

    st.markdown("### About This Demo")
    st.markdown(
        """
        This demo showcases Cardinal Element's capabilities:

        - **ICP Discovery:** Find B2B operator prospects automatically
        - **Prospect Research:** SEC EDGAR data enrichment
        - **ICP Scoring:** Fit analysis against target profile
        - **C-Suite Advisors:** AI agents for strategic guidance
        - **ODSC Demo:** Pre-cached walkthrough for presentations

        Built with Streamlit and Claude AI.
        """
    )

    st.markdown("### ICP Criteria")
    st.markdown(
        """
        - **Type:** B2B operators (not SaaS)
        - **Revenue:** $5M - $40M ARR
        - **Employees:** 20 - 150
        - **Industries:** Consulting, engineering, professional services,
          staffing, marketing, accounting
        """
    )

    st.markdown("### Example Searches")
    st.markdown(
        """
        Try these (pre-cached for instant results):
        - **EPAM** (IT Services)
        - **ACN** (Accenture)
        - **AAPL** (Apple -- contrast case)

        Or search any public company by ticker.
        """
    )
