"""
CLI entry point for C-Suite agents.

Provides commands to interact with individual agents, run cross-functional synthesis,
manage sessions, and generate reports.
"""

import asyncio
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
from csuite.session import SessionManager

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

    try:
        with console.status(f"[cyan]Consulting {agent.config.name}..."):
            response = run_async(agent.chat(question))
        agent.display_response(response)
    except Exception as e:
        console.print(Panel(
            f"[red bold]Error:[/red bold] {e}",
            title="[red]Agent Error[/red]",
            border_style="red",
        ))

    console.print(f"[dim]Session saved: {agent.get_session_id()}[/dim]\n")




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
    """Start an interactive session with agents.

    Use @agent to direct questions to specific agents:
    - @ceo - Ask the CEO
    - @cfo - Ask the CFO
    - @cto - Ask the CTO
    - @cmo - Ask the CMO
    - @coo - Ask the COO
    - @cpo - Ask the CPO
    - @cro - Ask the CRO

    Example:
        > @cfo What's our current utilization rate?
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
            "  [cyan]@feedback[/cyan] - Record feedback on a response\n\n"
            "Commands: [dim]/quit, /sessions, /clear[/dim]",
            border_style="blue",
        )
    )

    agents: dict[str, BaseAgent] = {}

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
            elif directive in AGENT_MAP:
                if directive not in agents:
                    agents[directive] = create_agent(directive)
                agent = agents[directive]
                try:
                    with console.status(f"[cyan]Consulting {agent.config.name}..."):
                        response = run_async(agent.chat(question))
                    agent.display_response(response)
                except Exception as e:
                    console.print(Panel(
                        f"[red bold]Error:[/red bold] {e}",
                        title="[red]Agent Error[/red]",
                        border_style="red",
                    ))
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

        try:
            with console.status(f"[cyan]Consulting {agent.config.name}..."):
                response = run_async(agent.chat(user_input))
            agent.display_response(response)
        except Exception as e:
            console.print(Panel(
                f"[red bold]Error:[/red bold] {e}",
                title="[red]Agent Error[/red]",
                border_style="red",
            ))


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


if __name__ == "__main__":
    cli()
