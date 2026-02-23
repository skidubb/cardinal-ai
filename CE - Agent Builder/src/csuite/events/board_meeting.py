"""
Board Meeting Event — structured interactive session with execs.

Extension of interactive mode with:
- Agenda-driven flow
- Session persistence to Notion
- Structured minutes output (decisions, action items)
"""

import time

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.agents.base import BaseAgent
from csuite.debate import DebateOrchestrator
from csuite.events import EventBase, EventResult
from csuite.events.notion_writer import _select_property, write_event_to_notion
from csuite.orchestrator import Orchestrator

AGENT_MAP: dict[str, type[BaseAgent]] = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "cto": CTOAgent,
    "cmo": CMOAgent,
    "coo": COOAgent,
    "cpo": CPOAgent,
    "cro": CROAgent,
}


def _run_async(coro):
    import asyncio
    return asyncio.run(coro)


class BoardMeetingEvent(EventBase):
    """Structured interactive board meeting with agenda, minutes, and Notion output."""

    event_type = "board_meeting"

    def __init__(
        self,
        topic: str,
        agenda: list[str] | None = None,
        agents: list[str] | None = None,
        output_path: str | None = None,
        **kwargs,
    ):
        super().__init__(topic=topic, agents=agents, **kwargs)
        self.agenda = agenda or []
        self.output_path = output_path
        self.console = Console()
        self.minutes: list[dict] = []  # {type, speaker, content}
        self.decisions: list[str] = []
        self.action_items: list[str] = []

    async def run(self) -> EventResult:
        """Run an interactive board meeting. Returns result when user ends session."""
        start_time = time.time()

        agents_label = ", ".join(r.upper() for r in self.agents)
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Board Meeting[/bold]\n\n"
                f"[dim]Topic:[/dim] {self.topic}\n"
                f"[dim]Agenda:[/dim] {', '.join(self.agenda) or 'Open'}\n"
                f"[dim]Attendees:[/dim] {agents_label}\n"
                f"[dim]Event ID:[/dim] {self.event_id}\n\n"
                "Directives:\n"
                "  [cyan]@ceo/@cfo/...@cro[/cyan] — Direct question to exec\n"
                "  [cyan]@all[/cyan] — All executives (synthesis)\n"
                "  [cyan]@debate[/cyan] — Open debate on topic\n"
                "  [cyan]/decision[/cyan] — Record a decision\n"
                "  [cyan]/action[/cyan] — Record an action item\n"
                "  [cyan]/agenda[/cyan] — Show remaining agenda\n"
                "  [cyan]/end[/cyan] — End meeting and generate minutes",
                border_style="bright_white",
            )
        )

        # Show agenda if provided
        if self.agenda:
            self.console.print()
            table = Table(title="Agenda")
            table.add_column("#", style="cyan", width=4)
            table.add_column("Item", style="white")
            for i, item in enumerate(self.agenda, 1):
                table.add_row(str(i), item)
            self.console.print(table)

        # Interactive loop
        active_agents: dict[str, BaseAgent] = {}
        orchestrator = Orchestrator()

        while True:
            try:
                user_input = Prompt.ask("\n[bold green]board>[/bold green]")
            except (KeyboardInterrupt, EOFError):
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Commands
            if user_input == "/end":
                break
            elif user_input.startswith("/decision "):
                decision = user_input[10:].strip()
                self.decisions.append(decision)
                self.minutes.append({
                    "type": "decision", "speaker": "Chairman", "content": decision,
                })
                self.console.print(f"[green]Decision recorded:[/green] {decision}")
                continue
            elif user_input.startswith("/action "):
                action = user_input[8:].strip()
                self.action_items.append(action)
                self.minutes.append({"type": "action", "speaker": "Chairman", "content": action})
                self.console.print(f"[green]Action item recorded:[/green] {action}")
                continue
            elif user_input == "/agenda":
                if self.agenda:
                    for i, item in enumerate(self.agenda, 1):
                        self.console.print(f"  {i}. {item}")
                else:
                    self.console.print("[dim]No formal agenda set.[/dim]")
                continue

            # Record chairman input
            self.minutes.append({"type": "question", "speaker": "Chairman", "content": user_input})

            # Parse @-directives
            if user_input.startswith("@"):
                parts = user_input.split(" ", 1)
                directive = parts[0][1:].lower()
                question = parts[1] if len(parts) > 1 else ""

                if not question:
                    self.console.print("[yellow]Please provide a question.[/yellow]")
                    continue

                if directive == "debate":
                    debate_orch = DebateOrchestrator()
                    debate = _run_async(debate_orch.run_debate(question, self.agents))
                    if debate.synthesis:
                        self.minutes.append({
                            "type": "debate",
                            "speaker": "All",
                            "content": debate.synthesis,
                        })
                elif directive in ["all", "synthesize"]:
                    synthesis = _run_async(orchestrator.synthesize(question))
                    self.minutes.append({
                        "type": "synthesis",
                        "speaker": "All",
                        "content": synthesis,
                    })
                elif directive in AGENT_MAP:
                    if directive not in active_agents:
                        active_agents[directive] = AGENT_MAP[directive]()
                    agent = active_agents[directive]
                    with self.console.status(f"[cyan]Consulting {agent.config.name}..."):
                        response = _run_async(agent.chat(question))
                    agent.display_response(response)
                    self.minutes.append({
                        "type": "response",
                        "speaker": agent.config.name,
                        "content": response,
                    })
                else:
                    self.console.print(f"[yellow]Unknown: {directive}[/yellow]")
            else:
                self.console.print(
                    "[yellow]Use @ceo/@cfo/.../@all/@debate or /decision /action /end[/yellow]"
                )

        # Build result
        elapsed = (time.time() - start_time) / 60
        metrics = self.cost_tracker.get_daily_metrics()
        total_cost = metrics.total_cost

        agent_outputs: dict[str, str] = {}
        for entry in self.minutes:
            if entry["type"] == "response":
                speaker = entry["speaker"]
                agent_outputs.setdefault(speaker, "")
                agent_outputs[speaker] += entry["content"] + "\n\n"

        markdown = self._format_minutes(elapsed, total_cost)

        if self.output_path:
            from pathlib import Path
            Path(self.output_path).write_text(markdown)
            self.console.print(f"\n[green]Minutes saved to:[/green] {self.output_path}")

        result = self._build_result(
            markdown_output=markdown,
            agent_outputs=agent_outputs,
            total_cost=total_cost,
            duration_minutes=elapsed,
        )

        # Write to Notion
        notion_url = await write_event_to_notion(
            result,
            extra_properties={
                "Agenda": ", ".join(self.agenda) if self.agenda else "Open",
                "Status": _select_property("Completed"),
            },
        )
        if notion_url:
            result.notion_url = notion_url
            self.console.print(f"[green]Notion page:[/green] {notion_url}")

        self.console.print(
            f"\n[dim]Board meeting completed in {elapsed:.1f} minutes | "
            f"Cost: ${total_cost:.2f} | ID: {self.event_id}[/dim]\n"
        )

        return result

    def _format_minutes(self, elapsed: float, total_cost: float) -> str:
        lines = [
            "# Board Meeting Minutes",
            "",
            f"**Topic:** {self.topic}",
            f"**Date:** {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Attendees:** {', '.join(r.upper() for r in self.agents)}",
            f"**Duration:** {elapsed:.1f} minutes",
            f"**Cost:** ${total_cost:.2f}",
            f"**Event ID:** {self.event_id}",
            "",
        ]

        if self.agenda:
            lines.extend(["## Agenda", ""])
            for i, item in enumerate(self.agenda, 1):
                lines.append(f"{i}. {item}")
            lines.append("")

        lines.extend(["---", "", "## Discussion", ""])

        for entry in self.minutes:
            if entry["type"] == "question":
                lines.append(f"**{entry['speaker']}:** {entry['content']}")
                lines.append("")
            elif entry["type"] == "response":
                lines.extend([f"### {entry['speaker']}", "", entry["content"], ""])
            elif entry["type"] in ("synthesis", "debate"):
                header = f"### {entry['type'].title()} (All Executives)"
                lines.extend([header, "", entry["content"], ""])
            elif entry["type"] == "decision":
                lines.append(f"> **DECISION:** {entry['content']}")
                lines.append("")
            elif entry["type"] == "action":
                lines.append(f"> **ACTION:** {entry['content']}")
                lines.append("")

        if self.decisions:
            lines.extend(["---", "", "## Decisions", ""])
            for i, d in enumerate(self.decisions, 1):
                lines.append(f"{i}. {d}")
            lines.append("")

        if self.action_items:
            lines.extend(["## Action Items", ""])
            for i, a in enumerate(self.action_items, 1):
                lines.append(f"- [ ] {a}")
            lines.append("")

        lines.extend(["---", f"*Generated by C-Suite Board Meeting | {self.event_id}*"])

        return "\n".join(lines)
