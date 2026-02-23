"""
Strategy Meeting Event — debate-then-synthesize as a single flow.

Phase 1: Each exec gives an independent take (parallel via orchestrator)
Phase 2: Multi-round debate on the topic (via DebateOrchestrator)
Phase 3: Final synthesis integrating debate outcomes (via orchestrator)

Pinecone KB queried before Phase 1 per Executive Debate Protocol.
"""

import time

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from csuite.debate import DebateOrchestrator
from csuite.events import EventBase, EventResult
from csuite.events.notion_writer import _select_property, write_event_to_notion
from csuite.formatters.dual_output import build_dual_artifact
from csuite.orchestrator import AgentPerspective, Orchestrator
from csuite.tracing.graph import ActionType, CausalGraph


class StrategyMeetingEvent(EventBase):
    """Debate-then-synthesize: independent takes, structured debate, final synthesis."""

    event_type = "strategy_meeting"

    def __init__(
        self,
        topic: str,
        agents: list[str] | None = None,
        rounds: int = 3,
        output_path: str | None = None,
        negotiate: bool = False,
        show_process: bool = False,
        **kwargs,
    ):
        super().__init__(topic=topic, agents=agents, **kwargs)
        self.rounds = rounds
        self.output_path = output_path
        self.negotiate = negotiate
        self.show_process = show_process
        self.console = Console()

    async def run(self) -> EventResult:
        start_time = time.time()
        orchestrator = Orchestrator()
        debate_orch = DebateOrchestrator(cost_tracker=self.cost_tracker)
        causal_graph = CausalGraph(event_id=self.event_id)

        agents_label = ", ".join(r.upper() for r in self.agents)
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Strategy Meeting[/bold]\n\n"
                f"[dim]Topic:[/dim] {self.topic}\n"
                f"[dim]Executives:[/dim] {agents_label}\n"
                f"[dim]Debate Rounds:[/dim] {self.rounds}\n"
                f"[dim]Event ID:[/dim] {self.event_id}",
                border_style="bright_white",
            )
        )

        # ── Phase 1: Independent perspectives ───────────────────────────
        self.console.print("\n[bold]Phase 1: Independent Perspectives[/bold]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Gathering {len(self.agents)} independent perspectives...",
                total=None,
            )
            perspectives = await orchestrator.query_agents_parallel(
                self.agents, self.topic  # type: ignore[arg-type]
            )
            progress.update(task, description="[green]All perspectives received")

        agent_outputs: dict[str, str] = {}
        for p in perspectives:
            agent_outputs[p.role] = p.response
            # Log to causal graph
            causal_graph.add_node(
                agent_role=p.role,
                action_type=ActionType.PROPOSE,
                content=p.response[:500],
            )
            self.console.print()
            self.console.print(
                Panel(
                    Markdown(p.response),
                    title=f"[bold]{p.name}[/bold]",
                    border_style="blue",
                )
            )

        # ── Phase 2: Structured debate ──────────────────────────────────
        self.console.print("\n[bold]Phase 2: Executive Debate[/bold]\n")

        if self.negotiate:
            self.console.print("[dim]Mode: Constraint Negotiation[/dim]")
            debate_session = await debate_orch.run_negotiation(
                question=self.topic,
                roles=self.agents,
                total_rounds=self.rounds,
                causal_graph=causal_graph,
            )
        else:
            debate_session = await debate_orch.run_debate(
                question=self.topic,
                roles=self.agents,
                total_rounds=self.rounds,
                causal_graph=causal_graph,
            )

        # ── Phase 3: Final synthesis ────────────────────────────────────
        self.console.print("\n[bold]Phase 3: Final Synthesis[/bold]\n")

        # Build combined perspectives from both phases for richer synthesis
        combined_perspectives = [
            AgentPerspective(
                role=p.role,
                name=p.name,
                response=(
                    f"## Initial Position\n\n{p.response}\n\n"
                    f"## After Debate\n\n"
                    f"{self._get_final_position(debate_session, p.role)}"
                ),
            )
            for p in perspectives
        ]

        synthesis_text, _usage = orchestrator.synthesize_perspectives(
            question=self.topic,
            perspectives=combined_perspectives,
        )

        # Log synthesis to causal graph
        phase1_node_ids = [
            nid for nid, n in causal_graph.nodes.items()
            if n.action_type == ActionType.PROPOSE
        ]
        causal_graph.add_node(
            agent_role="synthesis",
            action_type=ActionType.SYNTHESIZE,
            content=synthesis_text[:500],
            parent_ids=phase1_node_ids[:7],
        )

        self.console.print()
        self.console.print(
            Panel(
                Markdown(synthesis_text),
                title="[bold magenta]Strategy Meeting Synthesis[/bold magenta]",
                border_style="magenta",
            )
        )

        # ── Build result ────────────────────────────────────────────────
        elapsed = (time.time() - start_time) / 60
        metrics = self.cost_tracker.get_daily_metrics()
        total_cost = metrics.total_cost

        markdown = self._format_markdown(
            perspectives, debate_session, synthesis_text, elapsed, total_cost
        )

        if self.output_path:
            from pathlib import Path

            Path(self.output_path).write_text(markdown)
            self.console.print(f"\n[green]Output saved to:[/green] {self.output_path}")

        # Build dual artifact
        dual = build_dual_artifact(
            markdown_output=markdown,
            synthesis=synthesis_text,
            graph=causal_graph,
            event_topic=self.topic,
        )

        if self.show_process:
            self.console.print()
            self.console.print(
                Panel(
                    Markdown(dual.process_narrative),
                    title="[bold dim]Process Narrative[/bold dim]",
                    border_style="dim",
                )
            )

        result = self._build_result(
            markdown_output=markdown,
            agent_outputs=agent_outputs,
            synthesis=synthesis_text,
            process_narrative=dual.process_narrative,
            total_cost=total_cost,
            duration_minutes=elapsed,
        )

        # Write to Notion
        notion_url = await write_event_to_notion(
            result,
            extra_properties={
                "Participants": ", ".join(r.upper() for r in self.agents),
                "Status": _select_property("Completed"),
            },
        )
        if notion_url:
            result.notion_url = notion_url
            self.console.print(f"[green]Notion page:[/green] {notion_url}")

        self.console.print(
            f"\n[dim]Strategy meeting completed in {elapsed:.1f} minutes | "
            f"Cost: ${total_cost:.2f} | ID: {self.event_id}[/dim]\n"
        )

        return result

    def _get_final_position(self, debate_session, role: str) -> str:
        """Extract an agent's final-round argument from the debate."""
        if not debate_session.rounds:
            return "(no debate arguments)"
        last_round = debate_session.rounds[-1]
        for arg in last_round.arguments:
            if arg.role == role:
                return arg.content
        return "(did not participate in final round)"

    def _format_markdown(
        self, perspectives, debate_session, synthesis, elapsed, total_cost
    ) -> str:
        lines = [
            "# Strategy Meeting",
            "",
            f"**Topic:** {self.topic}",
            f"**Executives:** {', '.join(r.upper() for r in self.agents)}",
            f"**Debate Rounds:** {self.rounds}",
            f"**Event ID:** {self.event_id}",
            f"**Date:** {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Duration:** {elapsed:.1f} minutes",
            f"**Cost:** ${total_cost:.2f}",
            "",
            "---",
            "",
            "## Phase 1: Independent Perspectives",
            "",
        ]

        for p in perspectives:
            lines.extend([f"### {p.name}", "", p.response, ""])

        lines.extend(["---", "", "## Phase 2: Executive Debate", ""])

        for rnd in debate_session.rounds:
            round_label = {
                "opening": "Opening Positions",
                "rebuttal": "Rebuttals",
                "final": "Final Statements",
            }.get(rnd.round_type, rnd.round_type.title())
            lines.extend([f"### Round {rnd.round_number}: {round_label}", ""])
            for arg in rnd.arguments:
                lines.extend([f"#### {arg.agent_name}", "", arg.content, ""])

        lines.extend([
            "---",
            "",
            "## Phase 3: Final Synthesis",
            "",
            synthesis,
            "",
            "---",
            f"*Generated by C-Suite Strategy Meeting | {self.event_id}*",
        ])

        return "\n".join(lines)
