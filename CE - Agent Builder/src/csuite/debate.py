"""
Multi-Round Executive Debate Orchestrator.

Runs structured debates where executives argue, rebut each other, make concessions,
and converge through genuine back-and-forth across multiple rounds.

Design decisions:
- Parallel within rounds, sequential across rounds (asyncio.gather per round)
- Fresh agents per round — debate context passed via user message, not session history
- Zero changes to BaseAgent — context injection via user message prefix
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csuite.tracing.graph import CausalGraph

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.agents.base import BaseAgent
from csuite.agents.factory import create_agent
from csuite.config import get_settings
from csuite.prompts.debate_prompt import (
    DEBATE_FINAL_INSTRUCTIONS,
    DEBATE_OPENING_INSTRUCTIONS,
    DEBATE_REBUTTAL_INSTRUCTIONS,
    DEBATE_SYNTHESIS_PROMPT,
    NEGOTIATION_OPENING_INSTRUCTIONS,
    NEGOTIATION_REBUTTAL_INSTRUCTIONS,
    format_prior_arguments,
)
from csuite.session import (
    DebateArgument,
    DebateRound,
    DebateSession,
    DebateSessionManager,
)
from csuite.tools.cost_tracker import CostTracker, TaskType

# Agent class lookup
AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "cto": CTOAgent,
    "cmo": CMOAgent,
    "coo": COOAgent,
    "cpo": CPOAgent,
    "cro": CROAgent,
}

# Color scheme per role for Rich output
ROLE_STYLES: dict[str, tuple[str, str]] = {
    "ceo": ("red", "bold red"),
    "cfo": ("blue", "bold blue"),
    "cto": ("green", "bold green"),
    "cmo": ("yellow", "bold yellow"),
    "coo": ("cyan", "bold cyan"),
    "cpo": ("magenta", "bold magenta"),
    "cro": ("bright_red", "bold bright_red"),
}


class DebateOrchestrator:
    """Orchestrates multi-round structured debates between executive agents."""

    def __init__(self, cost_tracker: CostTracker | None = None):
        self.settings = get_settings()
        self.console = Console()
        self.session_manager = DebateSessionManager()
        self.cost_tracker = cost_tracker or CostTracker()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    async def run_negotiation(
        self,
        question: str,
        roles: list[str] | None = None,
        total_rounds: int = 3,
        output_path: str | None = None,
        causal_graph: CausalGraph | None = None,
    ) -> DebateSession:
        """Run a negotiation-mode debate with constraint propagation.

        Round 0: Each agent proposes plan + declares constraints.
        Round 1+: Each agent receives ALL peer constraints, must revise.
        """
        from csuite.coordination.constraints import ConstraintExtractor, ConstraintStore
        from csuite.tracing.graph import ActionType

        if roles is None:
            roles = ["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]

        start_time = time.time()
        constraint_store = ConstraintStore()
        extractor = ConstraintExtractor()

        debate = DebateSession(
            question=question,
            agent_roles=roles,
            total_rounds=total_rounds,
        )

        role_names = ", ".join(r.upper() for r in roles)
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Executive Negotiation[/bold]\n\n"
                f"[dim]Question:[/dim] {question}\n"
                f"[dim]Executives:[/dim] {role_names}\n"
                f"[dim]Rounds:[/dim] {total_rounds}\n"
                f"[dim]Mode:[/dim] Constraint Negotiation\n"
                f"[dim]Debate ID:[/dim] {debate.id}",
                border_style="bright_white",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            for round_num in range(1, total_rounds + 1):
                task = progress.add_task(
                    f"[cyan]Negotiation round {round_num}/{total_rounds}...",
                    total=None,
                )

                # Build prompts
                prior_args = debate.get_all_arguments_through_round(round_num - 1)
                formatted_history = format_prior_arguments(prior_args)

                if round_num == 1:
                    base_instructions = NEGOTIATION_OPENING_INSTRUCTIONS
                else:
                    peer_constraints_text = constraint_store.format_for_prompt()
                    base_instructions = NEGOTIATION_REBUTTAL_INSTRUCTIONS.format(
                        round_number=round_num,
                        total_rounds=total_rounds,
                        prior_arguments=formatted_history,
                        peer_constraints=peer_constraints_text,
                    )

                user_message = f"{base_instructions}\n\n**Question:** {question}"

                # Query agents in parallel
                async def query_agent(role: str, msg: str = user_message) -> DebateArgument:
                    agent = create_agent(role, cost_tracker=self.cost_tracker)
                    response = await agent.chat(
                        msg,
                        task_type=TaskType.EXECUTIVE_DEBATE,
                        causal_graph=causal_graph,
                    )
                    return DebateArgument(
                        role=role,
                        agent_name=agent.config.name,
                        content=response,
                        round_number=round_num,
                    )

                arguments = await asyncio.gather(*[query_agent(r) for r in roles])

                # Extract constraints from responses
                for arg in arguments:
                    constraints = extractor.extract(arg.role, arg.content)
                    constraint_store.add_many(constraints)
                    # Log constraint nodes to causal graph
                    if causal_graph:
                        for c in constraints:
                            causal_graph.add_node(
                                agent_role=arg.role,
                                action_type=ActionType.CONSTRAIN,
                                content=f"[{c.strength.value}] {c.description}",
                            )

                debate_round = DebateRound(
                    round_number=round_num,
                    round_type="negotiation",
                    arguments=list(arguments),
                )
                debate.add_round(debate_round)
                self.session_manager.save(debate)

                progress.update(
                    task,
                    description=f"[green]Negotiation round {round_num} complete "
                    f"({len(constraint_store.constraints)} constraints)",
                )
                self._display_round(debate_round)

            # Synthesis
            synth_task = progress.add_task("[cyan]Synthesizing negotiation...", total=None)
            synthesis = await self._synthesize_debate(question, debate)
            debate.set_synthesis(synthesis)
            self.session_manager.save(debate)

            if causal_graph:
                causal_graph.add_node(
                    agent_role="synthesis",
                    action_type=ActionType.SYNTHESIZE,
                    content=synthesis[:500],
                )

            progress.update(synth_task, description="[green]Synthesis complete")

        self.console.print()
        self.console.print(
            Panel(
                Markdown(synthesis),
                title="[bold bright_white]Negotiation Synthesis[/bold bright_white]",
                border_style="bright_white",
            )
        )

        elapsed = time.time() - start_time
        self.console.print(
            f"\n[dim]Negotiation completed in {elapsed / 60:.1f} minutes | "
            f"Constraints: {len(constraint_store.constraints)} | ID: {debate.id}[/dim]\n"
        )

        if output_path:
            transcript = self._format_debate_markdown(debate, elapsed)
            Path(output_path).write_text(transcript)
            self.console.print(f"[green]Transcript saved to:[/green] {output_path}\n")

        return debate

    async def run_debate(
        self,
        question: str,
        roles: list[str] | None = None,
        total_rounds: int = 3,
        output_path: str | None = None,
        causal_graph: CausalGraph | None = None,
    ) -> DebateSession:
        """Run a full multi-round debate.

        Args:
            question: The strategic question to debate
            roles: Which agent roles to include (default: all six)
            total_rounds: Number of debate rounds (2-5)
            output_path: Optional file path for markdown transcript

        Returns:
            Completed DebateSession
        """
        if roles is None:
            roles = ["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]

        start_time = time.time()

        # Create debate session
        debate = DebateSession(
            question=question,
            agent_roles=roles,
            total_rounds=total_rounds,
        )

        # Display header
        role_names = ", ".join(r.upper() for r in roles)
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Executive Debate[/bold]\n\n"
                f"[dim]Question:[/dim] {question}\n"
                f"[dim]Executives:[/dim] {role_names}\n"
                f"[dim]Rounds:[/dim] {total_rounds}\n"
                f"[dim]Debate ID:[/dim] {debate.id}",
                border_style="bright_white",
            )
        )

        # Run rounds sequentially
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            for round_num in range(1, total_rounds + 1):
                task = progress.add_task(
                    f"[cyan]Round {round_num}/{total_rounds} — "
                    f"Consulting {len(roles)} executives...",
                    total=None,
                )

                debate_round = await self._run_round(
                    round_num, total_rounds, roles, question, debate,
                    causal_graph=causal_graph,
                )
                debate.add_round(debate_round)

                # Save after each round for crash resilience
                self.session_manager.save(debate)

                progress.update(
                    task,
                    description=f"[green]Round {round_num}/{total_rounds} complete",
                )

                # Display round results
                self._display_round(debate_round)

            # Synthesis
            synth_task = progress.add_task(
                "[cyan]Synthesizing debate...", total=None
            )
            synthesis = await self._synthesize_debate(question, debate)
            debate.set_synthesis(synthesis)
            self.session_manager.save(debate)
            progress.update(synth_task, description="[green]Synthesis complete")

        # Display synthesis
        self.console.print()
        self.console.print(
            Panel(
                Markdown(synthesis),
                title="[bold bright_white]Debate Synthesis[/bold bright_white]",
                border_style="bright_white",
            )
        )

        # Elapsed time
        elapsed = time.time() - start_time
        elapsed_min = elapsed / 60
        self.console.print(
            f"\n[dim]Debate completed in {elapsed_min:.1f} minutes | "
            f"ID: {debate.id}[/dim]\n"
        )

        # Write markdown transcript if requested
        if output_path:
            transcript = self._format_debate_markdown(debate, elapsed)
            Path(output_path).write_text(transcript)
            self.console.print(f"[green]Transcript saved to:[/green] {output_path}\n")

        return debate

    async def _run_round(
        self,
        round_number: int,
        total_rounds: int,
        roles: list[str],
        question: str,
        debate: DebateSession,
        causal_graph: CausalGraph | None = None,
    ) -> DebateRound:
        """Execute one parallel round of debate."""
        # Determine round type
        if round_number == 1:
            round_type = "opening"
        elif round_number == total_rounds:
            round_type = "final"
        else:
            round_type = "rebuttal"

        # Build user message for each agent
        prior_args = debate.get_all_arguments_through_round(round_number - 1)
        formatted_history = format_prior_arguments(prior_args)

        if round_type == "opening":
            instructions = DEBATE_OPENING_INSTRUCTIONS
        elif round_type == "final":
            instructions = DEBATE_FINAL_INSTRUCTIONS.format(
                round_number=round_number,
                total_rounds=total_rounds,
                prior_arguments=formatted_history,
            )
        else:
            instructions = DEBATE_REBUTTAL_INSTRUCTIONS.format(
                round_number=round_number,
                total_rounds=total_rounds,
                prior_arguments=formatted_history,
            )

        user_message = f"{instructions}\n\n**Question:** {question}"

        # Query all agents in parallel — fresh agent per round
        async def query_agent(role: str) -> DebateArgument:
            agent = create_agent(role, cost_tracker=self.cost_tracker)
            response = await agent.chat(
                user_message,
                task_type=TaskType.EXECUTIVE_DEBATE,
            )
            return DebateArgument(
                role=role,
                agent_name=agent.config.name,
                content=response,
                round_number=round_number,
            )

        arguments = await asyncio.gather(*[query_agent(r) for r in roles])

        # Log to causal graph
        if causal_graph:
            from csuite.tracing.graph import ActionType
            action = ActionType.PROPOSE if round_number == 1 else ActionType.REVISE
            for arg in arguments:
                causal_graph.add_node(
                    agent_role=arg.role,
                    action_type=action,
                    content=arg.content[:500],
                )

        return DebateRound(
            round_number=round_number,
            round_type=round_type,
            arguments=list(arguments),
        )

    async def _synthesize_debate(
        self,
        question: str,
        debate: DebateSession,
    ) -> str:
        """Generate final synthesis from the complete debate."""
        all_args = debate.get_all_arguments_through_round(debate.total_rounds)
        formatted_history = format_prior_arguments(all_args)

        synthesis_prompt = (
            f"The following question was debated across {debate.total_rounds} rounds "
            f"by {len(debate.agent_roles)} executives:\n\n"
            f"**Question:** {question}\n\n"
            f"**Full Debate Transcript:**\n\n{formatted_history}\n\n"
            f"Please synthesize this debate."
        )

        response = self.client.messages.create(
            model=self.settings.default_model,
            max_tokens=4096,
            temperature=0.7,
            system=DEBATE_SYNTHESIS_PROMPT,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )

        # Log synthesis cost
        self.cost_tracker.log_usage(
            agent="SYNTHESIS",
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            task_type=TaskType.EXECUTIVE_DEBATE,
        )

        return response.content[0].text

    def _display_round(self, debate_round: DebateRound) -> None:
        """Display a completed round with color-coded panels."""
        round_label = {
            "opening": "Opening Positions",
            "rebuttal": "Rebuttals",
            "final": "Final Statements",
        }.get(debate_round.round_type, debate_round.round_type.title())

        self.console.print()
        self.console.print(
            f"[bold]--- Round {debate_round.round_number}: {round_label} ---[/bold]"
        )

        for arg in debate_round.arguments:
            border, title_style = ROLE_STYLES.get(
                arg.role, ("white", "bold white")
            )
            self.console.print()
            self.console.print(
                Panel(
                    Markdown(arg.content),
                    title=f"[{title_style}]{arg.agent_name}[/{title_style}]",
                    border_style=border,
                )
            )

    def _format_debate_markdown(
        self, debate: DebateSession, elapsed: float
    ) -> str:
        """Format the full debate as a markdown transcript."""
        roles_str = ", ".join(r.upper() for r in debate.agent_roles)
        elapsed_min = elapsed / 60

        lines = [
            "# Executive Debate Transcript",
            "",
            f"**Question:** {debate.question}",
            f"**Executives:** {roles_str}",
            f"**Rounds:** {debate.total_rounds}",
            f"**Debate ID:** {debate.id}",
            f"**Date:** {debate.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Duration:** {elapsed_min:.1f} minutes",
            "",
            "---",
            "",
        ]

        for rnd in debate.rounds:
            round_label = {
                "opening": "Opening Positions",
                "rebuttal": "Rebuttals",
                "final": "Final Statements",
            }.get(rnd.round_type, rnd.round_type.title())

            lines.append(f"## Round {rnd.round_number}: {round_label}")
            lines.append("")

            for arg in rnd.arguments:
                lines.append(f"### {arg.agent_name}")
                lines.append("")
                lines.append(arg.content)
                lines.append("")

            lines.append("---")
            lines.append("")

        if debate.synthesis:
            lines.append("## Synthesis")
            lines.append("")
            lines.append(debate.synthesis)
            lines.append("")

        lines.append("---")
        lines.append(f"*Generated by C-Suite Executive Debate | {datetime.now().isoformat()}*")

        return "\n".join(lines)
