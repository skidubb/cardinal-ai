"""
Prospect Report Export Module.

CTO Sprint 2 Deliverable 3: PDF Report Export.

Generates prospect research briefs as Markdown (and optionally PDF) files
that can be emailed to prospects after discovery calls.

Uses Jinja2-style string formatting (no dependency on Jinja2 itself)
to render branded templates with company data, ICP scoring, and
key findings.

PDF generation requires weasyprint (optional dependency).
If weasyprint is not installed, only Markdown export is available.

Usage:
    from csuite.tools.report_generator import ProspectReportGenerator

    generator = ProspectReportGenerator()
    md_content = generator.generate_markdown(company_info, financials, icp_fit)
    generator.save_markdown(md_content, "output/prospect_brief.md")
    generator.save_pdf(md_content, "output/prospect_brief.pdf")  # Requires weasyprint
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# Report Template (Markdown)
# ============================================================================

PROSPECT_BRIEF_TEMPLATE = """# Prospect Research Brief: {company_name}

**Prepared by:** Cardinal Element -- AI-Native Growth Architecture
**Date:** {date}
**Ticker:** {ticker}
**Industry:** {industry}

---

## Company Overview

| Metric | Value |
|--------|-------|
| Company Name | {company_name} |
| Stock Ticker | {ticker} |
| State | {state} |
| Industry (SIC) | {industry} |
| Entity Type | {entity_type} |

## Financial Summary

| Metric | Value |
|--------|-------|
| Annual Revenue | {revenue} |
| Net Income | {net_income} |
| Total Assets | {total_assets} |
| Employees | {employees} |
| Revenue per Employee | {revenue_per_employee} |

## ICP Fit Analysis

**Cardinal Element ICP:** B2B operators, $5M-$40M ARR, 20-150 employees

**Overall Fit:** {icp_label}

### Scoring Breakdown

{icp_reasons}

## Key Findings

{key_findings}

---

## About Cardinal Element

Cardinal Element is an AI-native growth architecture consultancy that replaces
executive advisory layers with AI agents optimized for B2B operators. Our
Growth Architecture Audit identifies where AI can replace human processes
across your revenue, operations, and technology functions.

**Contact:** Scott Ewalt | contact@cardinalelement.com

---

*This report was generated using Cardinal Element's AI-powered prospect research
pipeline. All financial data sourced from SEC EDGAR public filings.*

*Generated: {timestamp}*
"""


# ============================================================================
# Report Generator
# ============================================================================


def format_currency(value: float | None) -> str:
    """Format a number as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


class ProspectReportGenerator:
    """Generate prospect research briefs as Markdown and PDF.

    Usage:
        generator = ProspectReportGenerator()
        md = generator.generate_markdown(company_info, financials, icp_fit)
        generator.save_markdown(md, "output/brief.md")
    """

    def __init__(self, output_dir: str | Path | None = None):
        """Initialize report generator.

        Args:
            output_dir: Default directory for saving reports.
                       Defaults to ./reports/
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            project_root = Path(os.environ.get(
                "CSUITE_PROJECT_ROOT",
                Path(__file__).parent.parent.parent.parent
            ))
            self.output_dir = project_root / "reports"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown(
        self,
        company_info: Any,
        financials: Any | None = None,
        icp_fit: dict[str, Any] | None = None,
        agent_responses: dict[str, str] | None = None,
    ) -> str:
        """Generate a prospect brief in Markdown format.

        Args:
            company_info: CompanyInfo dataclass
            financials: FinancialData dataclass (optional)
            icp_fit: ICP fit scoring dict (optional)
            agent_responses: Dict of agent_name -> response text (optional)

        Returns:
            Markdown string
        """
        # Format financial values
        revenue = format_currency(financials.revenue) if financials else "N/A"
        net_income = format_currency(financials.net_income) if financials else "N/A"
        total_assets = format_currency(financials.total_assets) if financials else "N/A"

        if financials and financials.employees:
            employees = f"{financials.employees:,}"
        else:
            employees = "N/A"

        if financials and financials.revenue and financials.employees:
            rev_per_emp = format_currency(financials.revenue / financials.employees)
        else:
            rev_per_emp = "N/A"

        # Format ICP reasons
        if icp_fit and icp_fit.get("reasons"):
            icp_reasons = "\n".join(f"- {reason}" for reason in icp_fit["reasons"])
        else:
            icp_reasons = "- No ICP analysis available"

        icp_label = icp_fit.get("fit_label", "UNKNOWN") if icp_fit else "UNKNOWN"

        # Generate key findings
        findings = self._generate_key_findings(company_info, financials, icp_fit)

        # Fill template
        report = PROSPECT_BRIEF_TEMPLATE.format(
            company_name=company_info.name,
            date=datetime.now().strftime("%B %d, %Y"),
            ticker=company_info.ticker or "N/A",
            industry=company_info.sic_description or "N/A",
            state=company_info.state or "N/A",
            entity_type=company_info.entity_type or "N/A",
            revenue=revenue,
            net_income=net_income,
            total_assets=total_assets,
            employees=employees,
            revenue_per_employee=rev_per_emp,
            icp_label=icp_label,
            icp_reasons=icp_reasons,
            key_findings=findings,
            timestamp=datetime.now().isoformat(),
        )

        # Append agent responses if provided
        if agent_responses:
            report += "\n## C-Suite Agent Perspectives\n\n"
            for agent_name, response in agent_responses.items():
                report += f"### {agent_name} Analysis\n\n{response}\n\n"

        return report

    def _generate_key_findings(
        self,
        company_info: Any,
        financials: Any | None,
        icp_fit: dict[str, Any] | None,
    ) -> str:
        """Generate key findings section based on available data."""
        findings = []

        if financials and financials.revenue:
            if financials.revenue >= 1_000_000_000:
                findings.append(
                    f"**Enterprise Scale:** Revenue of {format_currency(financials.revenue)} "
                    "indicates a large enterprise. Cardinal Element typically serves mid-market "
                    "operators ($5-40M) but architectural patterns from large enterprises "
                    "can inform growth strategy."
                )
            elif 5_000_000 <= financials.revenue <= 40_000_000:
                findings.append(
                    f"**Target ICP Range:** Revenue of {format_currency(financials.revenue)} "
                    "places this company squarely in Cardinal Element's target market. "
                    "Companies at this scale benefit most from AI-augmented executive functions."
                )

        if company_info.sic_description:
            sic_lower = company_info.sic_description.lower()
            if any(kw in sic_lower for kw in ["services", "consulting", "professional"]):
                findings.append(
                    f"**B2B Services Industry:** {company_info.sic_description} is a "
                    "core ICP industry for Cardinal Element. Professional services firms "
                    "have the highest ROI from AI-native growth architecture."
                )

        if financials and financials.employees:
            if 20 <= financials.employees <= 150:
                findings.append(
                    f"**ICP Employee Range:** {financials.employees:,} employees is within "
                    "the 20-150 range where companies need executive-level guidance but "
                    "cannot justify full-time C-suite hires."
                )

        if not findings:
            findings.append(
                "Insufficient data for detailed findings."
                " Additional research recommended."
            )

        return "\n\n".join(findings)

    def save_markdown(self, content: str, filepath: str | Path | None = None) -> Path:
        """Save report as Markdown file.

        Args:
            content: Markdown content
            filepath: Output path (defaults to reports/{timestamp}.md)

        Returns:
            Path to saved file
        """
        if filepath:
            path = Path(filepath)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.output_dir / f"prospect_brief_{timestamp}.md"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def save_pdf(self, content: str, filepath: str | Path | None = None) -> Path | None:
        """Save report as PDF file.

        Requires weasyprint to be installed:
            pip install weasyprint

        Args:
            content: Markdown content
            filepath: Output path (defaults to reports/{timestamp}.pdf)

        Returns:
            Path to saved file, or None if weasyprint is not available
        """
        try:
            import markdown
            from weasyprint import HTML
        except ImportError:
            print(
                "PDF export requires weasyprint and markdown packages. "
                "Install with: pip install weasyprint markdown"
            )
            return None

        if filepath:
            path = Path(filepath)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.output_dir / f"prospect_brief_{timestamp}.pdf"

        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert markdown to HTML
        html_content = markdown.markdown(
            content,
            extensions=["tables", "fenced_code"],
        )

        # Wrap in styled HTML
        styled_html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 40px;
                    color: #0B1E3F;
                    line-height: 1.6;
                }}
                h1 {{ color: #0B1E3F; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }}
                h2 {{ color: #0B1E3F; margin-top: 30px; }}
                h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 10px 12px; text-align: left; }}
                th {{ background-color: #0B1E3F; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                hr {{ border: none; border-top: 2px solid #D4AF37; margin: 30px 0; }}
                strong {{ color: #0B1E3F; }}
                code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        HTML(string=styled_html).write_pdf(str(path))
        return path


def generate_prospect_report(
    company_info: Any,
    financials: Any | None = None,
    icp_fit: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
    format: str = "markdown",
) -> Path | None:
    """Convenience function to generate a prospect report.

    Args:
        company_info: CompanyInfo dataclass
        financials: FinancialData (optional)
        icp_fit: ICP scoring dict (optional)
        output_path: Output file path
        format: "markdown" or "pdf"

    Returns:
        Path to saved file
    """
    generator = ProspectReportGenerator()
    content = generator.generate_markdown(company_info, financials, icp_fit)

    if format == "pdf":
        return generator.save_pdf(content, output_path)
    else:
        return generator.save_markdown(content, output_path)
