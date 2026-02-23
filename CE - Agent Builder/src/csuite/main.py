"""
CLI entry point for C-Suite agents.

Provides commands to interact with individual agents, run cross-functional synthesis,
manage sessions, and generate reports.
"""

import asyncio
from datetime import UTC
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.agents.base import BaseAgent
from csuite.agents.factory import create_agent
from csuite.audit import run_audit
from csuite.debate import DebateOrchestrator
from csuite.orchestrator import AgentRole, Orchestrator
from csuite.session import DebateSessionManager, SessionManager

# Load environment variables
load_dotenv()

console = Console()

AGENT_MAP: dict[str, type[BaseAgent]] = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "cto": CTOAgent,
    "cmo": CMOAgent,
    "coo": COOAgent,
    "cpo": CPOAgent,
    "cro": CROAgent,
}


def run_async(coro):
    """Helper to run async functions in sync context."""
    return asyncio.run(coro)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """C-Suite: Your Elite AI Advisory Team

    A personal C-suite of AI advisors for consulting and agency businesses.
    Each agent provides deep domain expertise and actionable recommendations.
    """
    pass


# ============================================================================
# Individual Agent Commands
# ============================================================================


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def ceo(question: str, session: str | None):
    """Consult the Chief Executive Officer.

    Expertise: Strategic vision, competitive positioning, market dynamics, growth strategy.

    Example: csuite ceo "Should we expand into AI consulting?"
    """
    _query_agent("ceo", question, session)


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def cfo(question: str, session: str | None):
    """Consult the Chief Financial Officer.

    Expertise: Project profitability, cash flow, pricing strategy, financial KPIs.

    Example: csuite cfo "Analyze our Q4 project profitability"
    """
    _query_agent("cfo", question, session)


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def cto(question: str, session: str | None):
    """Consult the Chief Technology Officer.

    Expertise: Architecture review, security, build vs. buy, tech strategy.

    Example: csuite cto "Review our API architecture for scalability"
    """
    _query_agent("cto", question, session)


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def cmo(question: str, session: str | None):
    """Consult the Chief Marketing Officer.

    Expertise: Positioning, thought leadership, demand generation, brand strategy.

    Example: csuite cmo "Develop a thought leadership strategy for AI consulting"
    """
    _query_agent("cmo", question, session)


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def coo(question: str, session: str | None):
    """Consult the Chief Operating Officer.

    Expertise: Resource planning, delivery excellence, process optimization.

    Example: csuite coo "Optimize our resource allocation process"
    """
    _query_agent("coo", question, session)


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def cpo(question: str, session: str | None):
    """Consult the Chief Product Officer.

    Expertise: Service design, prioritization, product-market fit, roadmap strategy.

    Example: csuite cpo "How should we package our AI consulting offerings?"
    """
    _query_agent("cpo", question, session)


@cli.command()
@click.argument("question")
@click.option("--session", "-s", help="Resume a previous session by ID")
def cro(question: str, session: str | None):
    """Consult the Chief Revenue Officer.

    Expertise: Revenue strategy, pipeline management, GTM alignment, sales methodology.

    Example: csuite cro "How should we structure our pipeline for Q2?"
    """
    _query_agent("cro", question, session)


def _query_agent(role: str, question: str, session_id: str | None = None):
    """Internal function to query an agent."""
    agent = create_agent(role)

    if session_id and hasattr(agent, "resume_session"):
        if not agent.resume_session(session_id):
            console.print(f"[yellow]Session {session_id} not found. Starting new session.[/yellow]")

    console.print(f"\n[dim]Session: {agent.get_session_id()}[/dim]\n")

    with console.status(f"[cyan]Consulting {agent.config.name}..."):
        response = run_async(agent.chat(question))

    agent.display_response(response)

    console.print(f"[dim]Session saved: {agent.get_session_id()}[/dim]\n")


# ============================================================================
# Synthesis Command
# ============================================================================


@cli.command()
@click.argument("question")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Which agents to consult (default: all)",
)
def synthesize(question: str, agents: tuple):
    """Run cross-functional analysis with multiple agents.

    Consults multiple C-suite advisors and synthesizes their perspectives
    into a unified strategic recommendation.

    Example: csuite synthesize "Should we expand into AI consulting?"
    Example: csuite synthesize "Evaluate acquiring a competitor" --agents ceo cfo cto coo
    """
    orchestrator = Orchestrator()

    roles: list[AgentRole] | None = list(agents) if agents else None

    console.print("\n[bold]Cross-Functional Strategic Analysis[/bold]\n")
    console.print(f"[dim]Question: {question}[/dim]\n")

    run_async(orchestrator.synthesize(question, roles))


# ============================================================================
# Audit Command - $4.75 Growth Strategy Audit
# ============================================================================


@cli.command()
@click.argument("company_description")
@click.option("--revenue", help="Annual revenue (e.g., '$12M')")
@click.option("--employees", type=int, help="Employee count")
@click.option("--industry", help="Industry vertical")
@click.option("--output", "-o", type=click.Path(), help="Output file path for markdown report")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Agents to include (default: all seven)",
)
def audit(
    company_description: str,
    revenue: str | None,
    employees: int | None,
    industry: str | None,
    output: str | None,
    agents: tuple,
):
    """Run a Growth Strategy Audit on a business.

    Executes a comprehensive analysis with all six C-suite agents:
    - Unit economics and pricing analysis (CFO)
    - Competitive positioning review (CMO)
    - Strategic vision and market positioning (CEO)
    - Technology and infrastructure assessment (CTO)
    - Operations and scalability review (COO)
    - Product and service design analysis (CPO)
    - Strategic synthesis across all perspectives

    Target: ~$10-13 API cost, ~12-25 minutes execution time (all 6 agents).

    Example:
        csuite audit "A $12M professional services firm with 45 employees"

        csuite audit "Management consulting firm" \\
            --revenue "$12M" --employees 45 \\
            --industry "Professional Services" \\
            --output audit-acme.md

        csuite audit "Tech startup" -a cfo -a cto -o audit.md
    """
    selected = list(agents) if agents else None
    run_async(run_audit(company_description, revenue, employees, industry, output, selected))


# ============================================================================
# Debate Command
# ============================================================================


@cli.command()
@click.argument("question")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Which agents to include (default: all)",
)
@click.option(
    "--rounds",
    "-r",
    default=3,
    type=click.IntRange(2, 5),
    help="Number of debate rounds (2-5, default: 3)",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path for markdown transcript")
def debate(question: str, agents: tuple, rounds: int, output: str | None):
    """Run a multi-round executive debate.

    Executives argue, rebut each other, make concessions, and converge through
    genuine back-and-forth across multiple rounds.

    Example:
        csuite debate "Should we pivot to value-based pricing?" -a cfo cto cmo -r 3

        csuite debate "Should we offer a free mini-audit?" -o debate.md
    """
    orchestrator = DebateOrchestrator()
    roles: list[str] | None = list(agents) if agents else None

    run_async(orchestrator.run_debate(question, roles, rounds, output))


# ============================================================================
# Debate Management Commands
# ============================================================================


@cli.group()
def debates():
    """Manage past debate sessions."""
    pass


@debates.command("list")
@click.option("--limit", "-n", default=20, help="Number of debates to show")
def debates_list(limit: int):
    """List previous debate sessions."""
    manager = DebateSessionManager()
    debate_sessions = manager.list_sessions(limit)

    if not debate_sessions:
        console.print("[yellow]No debates found.[/yellow]")
        return

    table = Table(title="Debate Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Question", style="white")
    table.add_column("Agents", style="green")
    table.add_column("Rounds", justify="right")
    table.add_column("Status", style="dim")
    table.add_column("Date", style="dim")

    for d in debate_sessions:
        question_preview = d.question[:50] + ("..." if len(d.question) > 50 else "")
        agents_str = ", ".join(r.upper() for r in d.agent_roles)
        status_style = "green" if d.status == "completed" else "yellow"
        table.add_row(
            d.id,
            question_preview,
            agents_str,
            str(d.total_rounds),
            f"[{status_style}]{d.status}[/{status_style}]",
            d.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@debates.command("show")
@click.argument("debate_id")
def debates_show(debate_id: str):
    """Replay a debate in the terminal."""
    manager = DebateSessionManager()
    debate_session = manager.load(debate_id)

    if not debate_session:
        console.print(f"[red]Debate {debate_id} not found.[/red]")
        return

    # Display header
    roles_str = ", ".join(r.upper() for r in debate_session.agent_roles)
    console.print()
    console.print(
        Panel(
            f"[bold]Executive Debate[/bold]\n\n"
            f"[dim]Question:[/dim] {debate_session.question}\n"
            f"[dim]Executives:[/dim] {roles_str}\n"
            f"[dim]Rounds:[/dim] {debate_session.total_rounds}\n"
            f"[dim]Status:[/dim] {debate_session.status}\n"
            f"[dim]Date:[/dim] {debate_session.created_at.strftime('%Y-%m-%d %H:%M')}",
            border_style="bright_white",
        )
    )

    # Replay rounds
    from csuite.debate import ROLE_STYLES

    for rnd in debate_session.rounds:
        round_label = {
            "opening": "Opening Positions",
            "rebuttal": "Rebuttals",
            "final": "Final Statements",
        }.get(rnd.round_type, rnd.round_type.title())

        console.print()
        console.print(f"[bold]--- Round {rnd.round_number}: {round_label} ---[/bold]")

        for arg in rnd.arguments:
            border, title_style = ROLE_STYLES.get(arg.role, ("white", "bold white"))
            console.print()
            console.print(
                Panel(
                    Markdown(arg.content),
                    title=f"[{title_style}]{arg.agent_name}[/{title_style}]",
                    border_style=border,
                )
            )

    # Display synthesis
    if debate_session.synthesis:
        console.print()
        console.print(
            Panel(
                Markdown(debate_session.synthesis),
                title="[bold bright_white]Debate Synthesis[/bold bright_white]",
                border_style="bright_white",
            )
        )

    console.print()


# ============================================================================
# Session Management Commands
# ============================================================================


@cli.group()
def sessions():
    """Manage conversation sessions."""
    pass


@sessions.command("list")
@click.option(
    "--agent",
    "-a",
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Filter by agent",
)
@click.option("--limit", "-n", default=20, help="Number of sessions to show")
def sessions_list(agent: str | None, limit: int):
    """List previous sessions."""
    manager = SessionManager()
    sessions = manager.list_sessions(agent, limit)

    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    table = Table(title="Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Agent", style="green")
    table.add_column("Title / First Message", style="white")
    table.add_column("Messages", justify="right")
    table.add_column("Updated", style="dim")

    for s in sessions:
        title = s.title or (s.messages[0].content[:40] + "..." if s.messages else "Empty")
        table.add_row(
            s.id,
            s.agent_role.upper(),
            title,
            str(len(s.messages)),
            s.updated_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@sessions.command("resume")
@click.argument("session_id")
def sessions_resume(session_id: str):
    """Resume an interactive session."""
    manager = SessionManager()
    session = manager.load(session_id)

    if not session:
        console.print(f"[red]Session {session_id} not found.[/red]")
        return

    agent = AGENT_MAP[session.agent_role](session=session)

    console.print(f"\n[bold]Resuming session with {agent.config.name}[/bold]")
    console.print(f"[dim]Session: {session.id} | Messages: {len(session.messages)}[/dim]\n")

    # Show recent history
    if session.messages:
        console.print("[dim]Recent history:[/dim]")
        for msg in session.messages[-4:]:
            role_color = "blue" if msg.role == "assistant" else "green"
            preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            console.print(f"[{role_color}]{msg.role}:[/{role_color}] {preview}")
        console.print()

    # Interactive loop
    _interactive_loop(agent)


@sessions.command("fork")
@click.argument("session_id")
@click.argument("title")
def sessions_fork(session_id: str, title: str):
    """Fork a session to create a new branch."""
    manager = SessionManager()
    session = manager.load(session_id)

    if not session:
        console.print(f"[red]Session {session_id} not found.[/red]")
        return

    agent = AGENT_MAP[session.agent_role](session=session)
    forked = agent.fork_session(title)

    if forked:
        console.print(f"[green]Forked session created: {forked.id}[/green]")
        console.print(f"[dim]Title: {title}[/dim]")
    else:
        console.print("[red]Failed to fork session.[/red]")


# ============================================================================
# Interactive Mode
# ============================================================================


@cli.command()
def interactive():
    """Start an interactive session with all agents.

    Use @agent to direct questions to specific agents:
    - @ceo - Ask the CEO
    - @cfo - Ask the CFO
    - @cto - Ask the CTO
    - @cmo - Ask the CMO
    - @coo - Ask the COO
    - @cpo - Ask the CPO
    - @all or @synthesize - Get perspectives from all agents
    - @debate - Run a multi-round executive debate

    Example:
        > @cfo What's our current utilization rate?
        > @all Should we hire two more senior consultants?
        > @debate Should we pivot to value-based pricing?
    """
    console.print(
        Panel(
            "[bold]C-Suite Interactive Mode[/bold]\n\n"
            "Direct questions to specific executives:\n"
            "  [cyan]@ceo[/cyan] - Chief Executive Officer\n"
            "  [cyan]@cfo[/cyan] - Chief Financial Officer\n"
            "  [cyan]@cto[/cyan] - Chief Technology Officer\n"
            "  [cyan]@cmo[/cyan] - Chief Marketing Officer\n"
            "  [cyan]@coo[/cyan] - Chief Operating Officer\n"
            "  [cyan]@cpo[/cyan] - Chief Product Officer\n"
            "  [cyan]@cro[/cyan] - Chief Revenue Officer\n"
            "  [cyan]@all[/cyan] - All executives (synthesis)\n"
            "  [cyan]@debate[/cyan] - Multi-round debate\n"
            "  [cyan]@feedback[/cyan] - Record feedback on a response\n\n"
            "Commands: [dim]/quit, /sessions, /clear[/dim]",
            border_style="blue",
        )
    )

    agents: dict[str, BaseAgent] = {}
    orchestrator = Orchestrator()

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]>[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        user_input = user_input.strip()

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            if user_input == "/quit":
                console.print("[dim]Goodbye![/dim]")
                break
            elif user_input == "/clear":
                agents = {}
                console.print("[dim]Sessions cleared.[/dim]")
                continue
            elif user_input == "/sessions":
                for role, agent in agents.items():
                    console.print(f"  {role.upper()}: {agent.get_session_id()}")
                continue
            else:
                console.print(f"[yellow]Unknown command: {user_input}[/yellow]")
                continue

        # Parse agent directive
        if user_input.startswith("@"):
            parts = user_input.split(" ", 1)
            directive = parts[0][1:].lower()
            question = parts[1] if len(parts) > 1 else ""

            if not question:
                console.print("[yellow]Please provide a question after the directive.[/yellow]")
                continue

            if directive == "feedback":
                # @feedback <role> <msg_index> <type> [detail]
                fb_parts = question.split(maxsplit=3)
                if len(fb_parts) < 3:
                    console.print(
                        "[yellow]Usage: @feedback <role> <msg_index> <type> [detail][/yellow]"
                    )
                    continue
                fb_role, fb_idx_str, fb_type = fb_parts[0], fb_parts[1], fb_parts[2]
                fb_detail = fb_parts[3] if len(fb_parts) > 3 else ""
                if fb_role in agents:
                    agents[fb_role].record_feedback(int(fb_idx_str), fb_type, fb_detail)
                    console.print(f"[green]Feedback recorded for {fb_role.upper()}.[/green]")
                else:
                    console.print(f"[yellow]No active session for {fb_role}.[/yellow]")
                continue
            elif directive == "debate":
                debate_orch = DebateOrchestrator()
                run_async(debate_orch.run_debate(question))
            elif directive in ["all", "synthesize"]:
                run_async(orchestrator.synthesize(question))
            elif directive in AGENT_MAP:
                if directive not in agents:
                    agents[directive] = create_agent(directive)
                agent = agents[directive]
                with console.status(f"[cyan]Consulting {agent.config.name}..."):
                    response = run_async(agent.chat(question))
                agent.display_response(response)
            else:
                console.print(f"[yellow]Unknown agent: {directive}[/yellow]")
        else:
            console.print(
                "[yellow]Start with a directive: "
                "@ceo @cfo @cto @cmo @coo @cpo @cro @all[/yellow]"
            )


def _interactive_loop(agent: BaseAgent):
    """Run an interactive conversation loop with a single agent."""
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]>[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session saved. Goodbye![/dim]")
            break

        user_input = user_input.strip()

        if not user_input:
            continue

        if user_input == "/quit":
            console.print("[dim]Session saved. Goodbye![/dim]")
            break

        with console.status(f"[cyan]Consulting {agent.config.name}..."):
            response = run_async(agent.chat(user_input))

        agent.display_response(response)


# ============================================================================
# Report Generation
# ============================================================================


@cli.group()
def report():
    """Generate reports from agent analysis."""
    pass


@report.command("financial")
@click.option(
    "--period", default="quarterly",
    type=click.Choice(["monthly", "quarterly", "annual"]),
)
@click.option("--output", "-o", default="financial-report.md", help="Output file path")
def report_financial(period: str, output: str):
    """Generate a financial report with CFO analysis."""
    agent = CFOAgent()

    questions = {
        "monthly": (
            "Provide a monthly financial review including"
            " P&L analysis, key metrics, and cash position."
        ),
        "quarterly": (
            "Provide a quarterly financial review including P&L"
            " with variance analysis, key metrics dashboard,"
            " and strategic financial outlook."
        ),
        "annual": (
            "Provide an annual financial review including"
            " full-year P&L analysis, trend analysis, and"
            " strategic financial planning for next year."
        ),
    }

    console.print(f"\n[bold]Generating {period} financial report...[/bold]\n")

    with console.status("[cyan]Consulting CFO..."):
        response = run_async(agent.chat(questions[period]))

    # Save report
    output_path = Path(output)
    output_path.write_text(f"# {period.title()} Financial Report\n\n{response}")

    console.print(f"[green]Report saved to: {output_path}[/green]\n")
    agent.display_response(response)


@report.command("operations")
@click.option("--output", "-o", default="operations-assessment.md", help="Output file path")
def report_operations(output: str):
    """Generate an operations assessment report."""
    agent = COOAgent()

    question = """Provide a comprehensive operations assessment including:
    1. Resource utilization and capacity analysis
    2. Project delivery health overview
    3. Process efficiency metrics
    4. Team health indicators
    5. Key operational recommendations"""

    console.print("\n[bold]Generating operations assessment...[/bold]\n")

    with console.status("[cyan]Consulting COO..."):
        response = run_async(agent.chat(question))

    # Save report
    output_path = Path(output)
    output_path.write_text(f"# Operations Assessment Report\n\n{response}")

    console.print(f"[green]Report saved to: {output_path}[/green]\n")
    agent.display_response(response)


@report.command("strategic")
@click.option("--output", "-o", default="strategic-assessment.md", help="Output file path")
def report_strategic(output: str):
    """Generate a strategic assessment report with CEO analysis."""
    agent = CEOAgent()

    question = """Provide a comprehensive strategic assessment including:
    1. Market position and competitive landscape
    2. Growth opportunities and threats
    3. Strategic priorities for the next 12 months
    4. Key bets and trade-offs
    5. Executive team and organizational considerations"""

    console.print("\n[bold]Generating strategic assessment...[/bold]\n")

    with console.status("[cyan]Consulting CEO..."):
        response = run_async(agent.chat(question))

    # Save report
    output_path = Path(output)
    output_path.write_text(f"# Strategic Assessment Report\n\n{response}")

    console.print(f"[green]Report saved to: {output_path}[/green]\n")
    agent.display_response(response)


@report.command("prospect")
@click.argument("ticker")
@click.option("--format", "-f", "fmt", default="markdown", type=click.Choice(["markdown", "pdf"]))
@click.option("--output", "-o", default=None, help="Output file path")
def report_prospect(ticker: str, fmt: str, output: str | None):
    """Generate a prospect research brief from SEC EDGAR data.

    Example: csuite report prospect AAPL
    Example: csuite report prospect MSFT --format pdf -o prospect-msft.pdf
    """
    from csuite.tools.report_generator import ProspectReportGenerator
    from csuite.tools.sec_edgar import SECEdgarClient

    console.print(f"\n[bold]Generating prospect brief for {ticker}...[/bold]\n")

    async def _generate():
        client = SECEdgarClient()
        brief = await client.generate_prospect_brief(ticker)
        return brief

    with console.status("[cyan]Fetching SEC EDGAR data..."):
        brief = run_async(_generate())

    if not brief.company_info:
        console.print(f"[red]Company not found: {ticker}[/red]")
        return

    generator = ProspectReportGenerator()
    content = generator.generate_markdown(
        company_info=brief.company_info,
        financials=brief.financials,
        icp_fit=brief.icp_fit,
    )

    if fmt == "pdf":
        output_path = generator.save_pdf(content, output)
    else:
        output_path = generator.save_markdown(content, output)

    if output_path:
        console.print(f"[green]Report saved to:[/green] {output_path}\n")
        console.print(Markdown(content))
    else:
        console.print("[red]Failed to save report.[/red]")


@report.command("product")
@click.option("--output", "-o", default="product-strategy.md", help="Output file path")
def report_product(output: str):
    """Generate a product strategy report with CPO analysis."""
    agent = CPOAgent()

    question = """Provide a comprehensive product strategy assessment including:
    1. Current service portfolio health
    2. Product-market fit signals
    3. Prioritized roadmap recommendations
    4. What to build vs. what NOT to build
    5. Success criteria and measurement approach"""

    console.print("\n[bold]Generating product strategy report...[/bold]\n")

    with console.status("[cyan]Consulting CPO..."):
        response = run_async(agent.chat(question))

    # Save report
    output_path = Path(output)
    output_path.write_text(f"# Product Strategy Report\n\n{response}")

    console.print(f"[green]Report saved to: {output_path}[/green]\n")
    agent.display_response(response)


# ============================================================================
# Feedback Command
# ============================================================================


@cli.command()
@click.argument("session_id")
@click.argument("message_index", type=int)
@click.argument("feedback_type", type=click.Choice(["thumbs_up", "thumbs_down", "correction"]))
@click.argument("detail", default="")
def feedback(session_id: str, message_index: int, feedback_type: str, detail: str):
    """Record feedback on a specific agent response.

    Example:
        csuite feedback abc123 1 thumbs_up
        csuite feedback abc123 1 correction "Use value-based not cost-plus"
    """
    manager = SessionManager()
    session = manager.load(session_id)

    if not session:
        console.print(f"[red]Session {session_id} not found.[/red]")
        return

    agent = AGENT_MAP[session.agent_role](session=session)
    agent.record_feedback(message_index, feedback_type, detail)

    console.print(f"[green]Feedback recorded:[/green] {feedback_type}")
    if detail:
        console.print(f"[dim]Detail: {detail}[/dim]")


# ============================================================================
# Event Commands
# ============================================================================


@cli.command("strategy-meeting")
@click.argument("topic")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Which agents to include (default: all)",
)
@click.option(
    "--rounds",
    "-r",
    default=3,
    type=click.IntRange(2, 5),
    help="Number of debate rounds (2-5, default: 3)",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--negotiate", is_flag=True, help="Use constraint negotiation mode instead of debate")
@click.option(
    "--show-process", is_flag=True,
    help="Display process narrative alongside deliverable",
)
def strategy_meeting(
    topic: str, agents: tuple, rounds: int, output: str | None,
    negotiate: bool, show_process: bool,
):
    """Run a Strategy Meeting — debate-then-synthesize.

    Phase 1: Independent perspectives from each exec
    Phase 2: Multi-round structured debate (or negotiation with --negotiate)
    Phase 3: Final synthesis integrating all positions

    Example:
        csuite strategy-meeting "Should we pivot to PLG?"

        csuite strategy-meeting "Should we offer a free mini-audit?" \\
            -a cfo cto cmo -r 3 -o meeting.md --negotiate --show-process
    """
    from csuite.events.strategy_meeting import StrategyMeetingEvent

    roles = list(agents) if agents else None
    event = StrategyMeetingEvent(
        topic=topic,
        agents=roles,
        rounds=rounds,
        output_path=output,
        negotiate=negotiate,
        show_process=show_process,
    )
    run_async(event.run())


@cli.group()
def sprint():
    """Sprint planning and management."""
    pass


@sprint.command("start")
@click.option("--strategy-doc", type=click.Path(exists=True), help="Path to strategy document")
@click.option("--number", "-n", default=1, type=int, help="Sprint number")
@click.option("--start", "start_date", default="", help="Sprint start date (YYYY-MM-DD)")
@click.option("--end", "end_date", default="", help="Sprint end date (YYYY-MM-DD)")
@click.option("--goal", "-g", default="", help="Sprint goal (optional if strategy-doc provided)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Which agents to include (default: all)",
)
def sprint_start(
    strategy_doc: str | None,
    number: int,
    start_date: str,
    end_date: str,
    goal: str,
    output: str | None,
    agents: tuple,
):
    """Generate sprint plans from all executives.

    Each exec produces their sprint plan in parallel. Output includes a
    dispatch manifest of sub-agent tasks for Chairman approval.

    Example:
        csuite sprint start --strategy-doc meeting-output.md --number 4 \\
            --start 2026-03-01 --end 2026-03-14

        csuite sprint start -n 4 -g "Launch PLG tier" -o sprint4.md
    """
    from csuite.events.sprint import SprintEvent

    topic = goal or f"Sprint {number} planning"
    roles = list(agents) if agents else None
    event = SprintEvent(
        topic=topic,
        strategy_doc=strategy_doc,
        sprint_number=number,
        start_date=start_date,
        end_date=end_date,
        agents=roles,
        output_path=output,
    )
    run_async(event.run())


@cli.command("board-meeting")
@click.option("--agenda", help="Comma-separated agenda items")
@click.option("--topic", "-t", default="Board Meeting", help="Meeting topic")
@click.option("--output", "-o", type=click.Path(), help="Output file path for minutes")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
    help="Which agents to include (default: all)",
)
def board_meeting(agenda: str | None, topic: str, output: str | None, agents: tuple):
    """Run a structured Board Meeting with all executives.

    Interactive session with agenda tracking, decision recording,
    and automatic minutes generation.

    Example:
        csuite board-meeting --agenda "Q1 review, hiring plan, pricing update"

        csuite board-meeting -t "Sprint 3 Review" -o minutes.md
    """
    from csuite.events.board_meeting import BoardMeetingEvent

    agenda_items = [item.strip() for item in agenda.split(",")] if agenda else []
    roles = list(agents) if agents else None
    event = BoardMeetingEvent(
        topic=topic,
        agenda=agenda_items,
        agents=roles,
        output_path=output,
    )
    run_async(event.run())


# ============================================================================
# Evaluation Command
# ============================================================================


@cli.command("evaluate")
@click.option("--questions", "-q", default=5, type=click.IntRange(1, 20),
              help="Number of benchmark questions to run (max 15 built-in)")
@click.option("--output", "-o", default="evaluation-report.md", help="Output file path")
@click.option("--modes", "-m", multiple=True,
              default=("single", "context", "synthesize", "debate", "negotiate"),
              help="Which modes to test")
@click.option("--roles", "-a", multiple=True,
              type=click.Choice(["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]),
              help="Agents for multi-agent modes (default: cfo cmo cto)")
@click.option("--rounds", "-r", default=2, type=click.IntRange(1, 5),
              help="Debate/negotiation rounds (default: 2)")
@click.option("--no-tools", is_flag=True, default=False,
              help="Disable tool use for all agents (apples-to-apples comparison)")
def evaluate(
    questions: int,
    output: str,
    modes: tuple,
    roles: tuple,
    rounds: int,
    no_tools: bool,
):
    """Run the multi-agent evaluation benchmark.

    Compares 5 execution modes on strategic questions, scored by a blind Opus judge.

    Example:
        csuite evaluate -q 1 -o /tmp/eval-test.md

        csuite evaluate -q 5 -m single -m debate -a cfo -a cmo -a cto -r 2
    """
    from csuite.evaluation.benchmark import BENCHMARK_QUESTIONS, BenchmarkRunner
    from csuite.evaluation.judge import BlindJudge
    from csuite.evaluation.report import EvaluationReport

    role_list = list(roles) if roles else ["cfo", "cmo", "cto"]
    mode_list = list(modes)

    console.print("\n[bold]Multi-Agent Evaluation Benchmark[/bold]\n")
    console.print(f"[dim]Questions: {questions} | Modes: {', '.join(mode_list)}[/dim]")
    agents_str = ", ".join(r.upper() for r in role_list)
    console.print(f"[dim]Agents: {agents_str} | Rounds: {rounds}[/dim]\n")

    if no_tools:
        console.print("[yellow]Tools disabled for all agents[/yellow]\n")

    runner = BenchmarkRunner(roles=role_list, rounds=rounds, silent=True, disable_tools=no_tools)
    judge = BlindJudge()

    async def _run():
        import json as _json
        import random
        import uuid
        from datetime import datetime

        from csuite.storage.duckdb_store import DuckDBStore

        # Run benchmark
        with console.status("[cyan]Running benchmark..."):
            benchmark = await runner.run_full_benchmark(
                num_questions=questions, modes=mode_list,
            )
        # Restore tools for judge calls
        runner.restore_settings()

        # --- Save raw outputs ---
        raw_outputs: dict[str, dict[str, dict]] = {}
        for q_id, q_results in benchmark.results.items():
            raw_outputs[q_id] = {}
            for mode, mr in q_results.items():
                raw_outputs[q_id][mode] = {
                    "text": mr.output_text,
                    "cost": mr.cost,
                    "duration": mr.duration_seconds,
                    "input_tokens": mr.input_tokens,
                    "output_tokens": mr.output_tokens,
                    "trace_metrics": mr.trace_metrics,
                }

        outputs_path = Path("evaluation-v2-outputs.json")
        outputs_path.write_text(_json.dumps(raw_outputs, indent=2))
        console.print(f"[green]Raw outputs saved:[/green] {outputs_path}")

        # --- Generate double-blind doc ---
        blind_lines = ["# Evaluation v2 — Double-Blind Responses\n"]
        key_mapping: dict[str, dict[str, str]] = {}
        for q_id, q_results in benchmark.results.items():
            q_text = next(
                (q["text"] for q in BENCHMARK_QUESTIONS if q["id"] == q_id), q_id
            )
            blind_lines.append(f"\n## Question: {q_id}\n")
            blind_lines.append(f"> {q_text}\n")

            mode_items = list(q_results.items())
            random.shuffle(mode_items)
            key_mapping[q_id] = {}
            for i, (mode, mr) in enumerate(mode_items, 1):
                label = f"Response {i}"
                key_mapping[q_id][label] = mode
                blind_lines.append(f"\n### {label}\n")
                blind_lines.append(mr.output_text)
                blind_lines.append("\n")

        blind_path = Path("evaluation-v2-double-blind.md")
        blind_path.write_text("\n".join(blind_lines))
        console.print(f"[green]Double-blind doc saved:[/green] {blind_path}")

        key_path = Path("evaluation-v2-key.json")
        key_path.write_text(_json.dumps(key_mapping, indent=2))
        console.print(f"[green]Key mapping saved:[/green] {key_path}")

        # Judge each question
        judge_results = {}
        for q_id, q_results in benchmark.results.items():
            with console.status(f"[cyan]Judging {q_id}..."):
                responses = {mode: mr.output_text for mode, mr in q_results.items()}
                judge_results[q_id] = judge.evaluate(responses)

        # --- Persist to DuckDB ---
        store = DuckDBStore()
        now = datetime.now(UTC).isoformat()
        for q_id, q_results in benchmark.results.items():
            for mode, mr in q_results.items():
                jr = judge_results.get(q_id)
                scores = jr.scores.get(mode, {}) if jr else {}
                store.save_evaluation_run({
                    "id": str(uuid.uuid4()),
                    "question_id": q_id,
                    "mode": mode,
                    "output_text": mr.output_text,
                    "cost": mr.cost,
                    "duration_seconds": mr.duration_seconds,
                    "judge_scores": scores,
                    "trace_metrics": mr.trace_metrics,
                    "created_at": now,
                })
        row_count = len(benchmark.results) * len(mode_list)
        console.print(f"[green]DuckDB persisted:[/green] {row_count} rows")

        # Generate report
        report = EvaluationReport()
        md = report.render(benchmark, judge_results)

        output_path = Path(output)
        output_path.write_text(md)
        console.print(f"\n[green]Report saved to:[/green] {output_path}\n")
        console.print(Markdown(md))

    run_async(_run())


if __name__ == "__main__":
    cli()
