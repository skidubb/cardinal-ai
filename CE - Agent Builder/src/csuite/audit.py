"""
Growth Strategy Audit pipeline.

Extracted from main.py to keep the CLI entry point thin.
Runs all six C-suite agents sequentially, then synthesizes their perspectives.
"""

import time
import uuid
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.config import get_settings
from csuite.formatters.audit_formatter import AuditFormatter, AuditMetrics
from csuite.orchestrator import AgentPerspective, Orchestrator
from csuite.tools.cost_tracker import CostTracker, TaskType

console = Console()

PINECONE_KB_INSTRUCTION = """
IMPORTANT: Before writing your analysis, use the pinecone_search_knowledge tool to query
the Cardinal Element GTM knowledge base for relevant frameworks, benchmarks, and insights
related to this company and industry. Ground your recommendations in proven frameworks
from the knowledge base where applicable."""

# Data-driven audit agent configuration
AUDIT_AGENTS: dict[str, dict] = {
    "cfo": {
        "class": CFOAgent,
        "title": "Financial Analysis",
        "name": "Chief Financial Officer",
        "task_type": TaskType.FINANCIAL_MODELING,
        "color": "blue",
        "prompt": """Perform a comprehensive financial analysis for this business:

{context}

Please analyze:
1. **Unit Economics Assessment**
   - Revenue per employee estimates
   - Gross margin analysis
   - Customer acquisition cost considerations
   - Lifetime value indicators

2. **Pricing Model Analysis**
   - Current pricing structure assessment
   - Value-based pricing opportunities
   - Competitive pricing positioning
   - Pricing optimization recommendations

3. **Cash Flow Stress Test**
   - Revenue concentration risks
   - Working capital considerations
   - Seasonal cash flow patterns
   - Buffer and runway recommendations

Provide specific, actionable recommendations with financial reasoning.""",
    },
    "cmo": {
        "class": CMOAgent,
        "title": "Competitive Positioning",
        "name": "Chief Marketing Officer",
        "task_type": TaskType.COMPETITIVE_ANALYSIS,
        "color": "green",
        "prompt": """Perform a competitive positioning analysis for this business:

{context}

Please analyze:
1. **Market Position Assessment**
   - Current positioning in the market
   - Differentiation factors
   - Brand perception indicators

2. **Competitive Landscape**
   - Key competitor categories
   - Competitive advantages and gaps
   - Market share considerations

3. **Go-to-Market Optimization**
   - Channel effectiveness
   - Messaging and value proposition
   - Demand generation opportunities

4. **Positioning Recommendations**
   - Strategic positioning options
   - Messaging framework suggestions
   - Priority marketing investments

Provide specific, actionable recommendations for competitive positioning.""",
    },
    "ceo": {
        "class": CEOAgent,
        "title": "Strategic Vision",
        "name": "Chief Executive Officer",
        "task_type": TaskType.EXECUTIVE_SYNTHESIS,
        "color": "yellow",
        "prompt": """Perform a strategic assessment for this business:

{context}

Please analyze:
1. **Market Position & Competitive Moat**
   - Current market positioning and defensibility
   - Competitive advantages and vulnerabilities
   - Industry trends and tailwinds/headwinds

2. **Growth Trajectory**
   - Revenue growth path and milestones
   - Expansion opportunities (new markets, services, segments)
   - Strategic partnerships and alliances

3. **Leadership Priorities**
   - Top 3-5 strategic priorities for next 12 months
   - Key bets and trade-offs
   - Organizational readiness for growth

4. **Risk Assessment**
   - Strategic risks and mitigation
   - Market disruption threats
   - Concentration risks (client, revenue, talent)

Provide specific, actionable strategic recommendations with clear prioritization.""",
    },
    "cto": {
        "class": CTOAgent,
        "title": "Technology & Infrastructure",
        "name": "Chief Technology Officer",
        "task_type": TaskType.INDUSTRY_RESEARCH,
        "color": "cyan",
        "prompt": """Perform a technology and infrastructure assessment for this business:

{context}

Please analyze:
1. **Technology Stack Evaluation**
   - Current tech stack fitness for scale
   - Technical debt indicators
   - Architecture scalability assessment

2. **AI & Automation Opportunities**
   - Processes ripe for AI automation
   - Build vs. buy analysis for key tools
   - AI readiness and data infrastructure

3. **Infrastructure Scalability**
   - Current infrastructure capacity
   - Scaling bottlenecks and solutions
   - Cloud/hosting optimization

4. **Security & Compliance**
   - Security posture assessment
   - Data governance considerations
   - Compliance requirements for growth

Provide specific, actionable technology recommendations with implementation priorities.""",
    },
    "coo": {
        "class": COOAgent,
        "title": "Operations & Scalability",
        "name": "Chief Operating Officer",
        "task_type": TaskType.INDUSTRY_RESEARCH,
        "color": "red",
        "prompt": """Perform an operational readiness and scalability assessment for this business:

{context}

Please analyze:
1. **Operational Efficiency**
   - Process maturity assessment
   - Resource utilization analysis
   - Operational bottlenecks

2. **Scaling Readiness**
   - Current capacity vs. growth targets
   - Delivery model scalability
   - Hiring/staffing plan alignment

3. **Process Optimization**
   - SOPs and knowledge management
   - Cross-functional coordination
   - Quality assurance and delivery standards

4. **Delivery Capacity**
   - Project management maturity
   - Client onboarding efficiency
   - Capacity planning recommendations

Provide specific, actionable operational recommendations with implementation timeline.""",
    },
    "cpo": {
        "class": CPOAgent,
        "title": "Product & Service Design",
        "name": "Chief Product Officer",
        "task_type": TaskType.INDUSTRY_RESEARCH,
        "color": "magenta",
        "prompt": """Perform a product and service design assessment for this business:

{context}

Please analyze:
1. **Service Portfolio Health**
   - Current service offerings assessment
   - Packaging and tier structure
   - Pricing alignment with value delivered

2. **Product-Market Fit**
   - ICP alignment and client feedback signals
   - Win/loss patterns
   - Competitive differentiation

3. **Client Experience**
   - Onboarding and delivery experience
   - Retention and expansion signals
   - NPS/satisfaction indicators

4. **Roadmap Priorities**
   - New service opportunities
   - Sunset candidates
   - Build sequence recommendations

Provide specific, actionable product/service recommendations with prioritized roadmap.""",
    },
    "cro": {
        "class": CROAgent,
        "title": "Revenue & GTM Analysis",
        "name": "Chief Revenue Officer",
        "task_type": TaskType.INDUSTRY_RESEARCH,
        "color": "bright_red",
        "prompt": """Perform a revenue and go-to-market assessment for this business:

{context}

Please analyze:
1. **Revenue Architecture**
   - Current revenue model assessment (recurring, project, hybrid)
   - Pipeline health and coverage ratios
   - Sales cycle analysis and velocity metrics
   - Revenue concentration risk

2. **GTM Motion**
   - Current go-to-market approach effectiveness
   - Channel mix optimization (direct, partner, inbound, outbound)
   - ICP alignment and market segmentation
   - Account-Based Marketing readiness

3. **Sales Effectiveness**
   - Win rate analysis and competitive positioning
   - Deal qualification rigor (MEDDPICC readiness)
   - Sales methodology and process maturity
   - Rep productivity and quota attainment

4. **Revenue Retention & Expansion**
   - Net Revenue Retention assessment
   - Client expansion motion design
   - Churn risk factors and prevention
   - Customer success infrastructure

Provide specific, actionable revenue recommendations with quantified impact estimates.""",
    },
}

# Default order for audit agents
AUDIT_AGENT_ORDER = ["cfo", "cmo", "ceo", "cto", "coo", "cpo", "cro"]


def _calculate_synthesis_cost(usage) -> float:
    """Calculate cost from API usage based on Feb 2026 Anthropic pricing."""
    settings = get_settings()
    model = settings.default_model
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens

    # Per-million-token pricing (Feb 2026)
    if "opus" in model:
        input_cost_per_mtok, output_cost_per_mtok = 5.0, 25.0
    elif "sonnet" in model:
        input_cost_per_mtok, output_cost_per_mtok = 3.0, 15.0
    else:  # haiku
        input_cost_per_mtok, output_cost_per_mtok = 1.0, 5.0

    return (input_tokens * input_cost_per_mtok + output_tokens * output_cost_per_mtok) / 1_000_000


async def run_audit(
    company_description: str,
    revenue: str | None,
    employees: int | None,
    industry: str | None,
    output_path: str | None,
    selected_agents: list[str] | None = None,
) -> None:
    """Execute the Growth Strategy Audit with all six C-suite agents."""
    # Generate unique audit ID for cost tracking
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    start_time = time.time()

    # Determine which agents to run
    agent_roles = selected_agents or AUDIT_AGENT_ORDER
    # Preserve canonical order
    agent_roles = [r for r in AUDIT_AGENT_ORDER if r in agent_roles]

    # Initialize shared cost tracker for all agents
    cost_tracker = CostTracker()

    # Initialize formatter
    formatter = AuditFormatter(
        company_description=company_description,
        revenue=revenue,
        employees=employees,
        industry=industry,
    )

    # Truncate long company description for display
    desc_preview = company_description[:60]
    desc_suffix = "..." if len(company_description) > 60 else ""
    agents_label = ", ".join(r.upper() for r in agent_roles)

    console.print()
    console.print(
        Panel(
            f"[bold]Growth Strategy Audit[/bold]\n\n"
            f"[dim]Company:[/dim] {desc_preview}{desc_suffix}\n"
            f"[dim]Agents:[/dim] {agents_label}\n"
            f"[dim]Audit ID:[/dim] {audit_id}",
            border_style="magenta",
        )
    )
    console.print()

    # Build the context prompt for agents
    context_parts = [f"Company Description: {company_description}"]
    if revenue:
        context_parts.append(f"Annual Revenue: {revenue}")
    if employees:
        context_parts.append(f"Employees: {employees}")
    if industry:
        context_parts.append(f"Industry: {industry}")
    context_prompt = "\n".join(context_parts)

    # Track costs per agent
    cost_by_agent: dict[str, float] = {}
    query_count = 0
    agent_responses: dict[str, str] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # =================================================================
        # Run each agent sequentially
        # =================================================================
        for role in agent_roles:
            cfg = AUDIT_AGENTS[role]
            task = progress.add_task(
                f"[{cfg['color']}]{role.upper()}: Analyzing {cfg['title'].lower()}...",
                total=None,
            )

            agent = cfg["class"](cost_tracker=cost_tracker)
            prompt = cfg["prompt"].format(context=context_prompt) + PINECONE_KB_INSTRUCTION

            response = await agent.chat(
                prompt,
                task_type=cfg["task_type"],
                audit_id=audit_id,
            )
            agent_cost = agent.get_session_cost_summary()
            cost_by_agent[role.upper()] = agent_cost["total_cost"]
            query_count += agent_cost["query_count"]
            agent_responses[role] = response

            progress.update(task, description=f"[green]{role.upper()}: Analysis complete ✓")

            # Display response
            console.print()
            console.print(
                Panel(
                    Markdown(response),
                    title=f"[bold {cfg['color']}]{cfg['name']}[/bold {cfg['color']}]",
                    border_style=cfg["color"],
                )
            )

            formatter.add_section(
                title=cfg["title"],
                source_agent=cfg["name"],
                content=response,
            )

        # =================================================================
        # Synthesis - Unified Recommendations across all agents
        # =================================================================
        task_synth = progress.add_task(
            "[cyan]Synthesizing strategic recommendations...", total=None
        )

        orchestrator = Orchestrator()

        perspectives = [
            AgentPerspective(
                role=role,
                name=AUDIT_AGENTS[role]["name"],
                response=agent_responses[role],
            )
            for role in agent_roles
        ]

        synthesis_response, synthesis_usage = orchestrator.synthesize_perspectives(
            question=f"Growth Strategy Audit for: {company_description}",
            perspectives=perspectives,
        )

        cost_by_agent["Synthesis"] = _calculate_synthesis_cost(synthesis_usage)
        query_count += 1

        progress.update(task_synth, description="[green]Synthesis complete ✓")

        # Display synthesis
        console.print()
        console.print(
            Panel(
                Markdown(synthesis_response),
                title="[bold magenta]Strategic Synthesis[/bold magenta]",
                border_style="magenta",
            )
        )

        formatter.set_synthesis(synthesis_response)

    # =========================================================================
    # Calculate and Display Metrics
    # =========================================================================
    elapsed_time = time.time() - start_time
    elapsed_minutes = elapsed_time / 60

    # Get actual costs from tracker
    audit_costs = cost_tracker.get_cost_per_audit(audit_id)
    total_cost = audit_costs.get("total_cost", sum(cost_by_agent.values()))

    # Update cost_by_agent with actual tracked costs if available
    if audit_costs.get("found") and audit_costs.get("cost_by_agent"):
        cost_by_agent = audit_costs["cost_by_agent"]

    metrics = AuditMetrics(
        total_cost=total_cost,
        query_count=query_count,
        execution_time_minutes=elapsed_minutes,
        cost_by_agent=cost_by_agent,
    )
    formatter.set_metrics(metrics)

    # Display metrics panel
    agent_count = len(agent_roles)
    console.print()
    console.print(
        Panel(
            f"[bold]Audit Complete[/bold]\n\n"
            f"[yellow]Agents:[/yellow] {agent_count}\n"
            f"[yellow]API Cost:[/yellow] ${total_cost:.2f}\n"
            f"[yellow]Queries:[/yellow] {query_count}\n"
            f"[yellow]Time:[/yellow] {elapsed_minutes:.1f} minutes",
            title="[bold cyan]Audit Metrics[/bold cyan]",
            border_style="cyan",
        )
    )

    # =========================================================================
    # Save Output File (if requested)
    # =========================================================================
    if output_path:
        output_file = Path(output_path)
        output_file.write_text(formatter.format_markdown())
        console.print(f"\n[green]Report saved to:[/green] {output_file}")

    console.print()
