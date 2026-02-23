"""
Sprint Planning Event — parallel exec planning from a strategy document.

Input: Strategy doc path + sprint number + date range
Output: 7 exec plans + dispatch manifest for sub-agent tasks
"""

import time
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from csuite.events import EventBase, EventResult
from csuite.events.notion_writer import _select_property, write_event_to_notion
from csuite.orchestrator import Orchestrator

SPRINT_PLAN_PROMPT = """You are participating in Sprint Planning for Cardinal Element.

**Sprint {sprint_number}** | {start_date} to {end_date}

Below is the strategy document that governs this sprint's priorities:

---
{strategy_content}
---

As the {role_title}, produce your sprint plan with:

1. **Your Top 3 Priorities** for this sprint (specific, measurable, time-bound)
2. **Deliverables** — concrete artifacts you will produce, with due dates
3. **Sub-Agent Dispatch List** — specific tasks to delegate to your sub-agents:
   - Task description, assigned sub-agent, expected output, deadline
4. **Dependencies** — what you need from other executives to execute
5. **Risk Flags** — what could derail your sprint plan

Format deliverables as a checklist:
- [ ] Deliverable name | Due: YYYY-MM-DD | Owner: Sub-agent name

Be specific to Cardinal Element's context as an AI-native growth architecture \
consultancy targeting B2B operators ($5-40M ARR)."""


class SprintEvent(EventBase):
    """Parallel exec sprint planning from a strategy document."""

    event_type = "sprint"

    def __init__(
        self,
        topic: str,
        strategy_doc: str | None = None,
        sprint_number: int = 1,
        start_date: str = "",
        end_date: str = "",
        agents: list[str] | None = None,
        output_path: str | None = None,
        **kwargs,
    ):
        super().__init__(topic=topic, agents=agents, **kwargs)
        self.strategy_doc = strategy_doc
        self.sprint_number = sprint_number
        self.start_date = start_date
        self.end_date = end_date
        self.output_path = output_path
        self.console = Console()

    async def run(self) -> EventResult:
        start_time = time.time()
        orchestrator = Orchestrator()

        # Load strategy doc if provided
        strategy_content = ""
        if self.strategy_doc:
            doc_path = Path(self.strategy_doc)
            if doc_path.exists():
                strategy_content = doc_path.read_text()
            else:
                self.console.print(
                    f"[yellow]Strategy doc not found: {self.strategy_doc}[/yellow]"
                )
                strategy_content = self.topic
        else:
            strategy_content = self.topic

        agents_label = ", ".join(r.upper() for r in self.agents)
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Sprint {self.sprint_number} Planning[/bold]\n\n"
                f"[dim]Goal:[/dim] {self.topic}\n"
                f"[dim]Dates:[/dim] {self.start_date} to {self.end_date}\n"
                f"[dim]Executives:[/dim] {agents_label}\n"
                f"[dim]Event ID:[/dim] {self.event_id}",
                border_style="bright_white",
            )
        )

        # Role title mapping
        role_titles = {
            "ceo": "Chief Executive Officer",
            "cfo": "Chief Financial Officer",
            "cto": "Chief Technology Officer",
            "cmo": "Chief Marketing Officer",
            "coo": "Chief Operating Officer",
            "cpo": "Chief Product Officer",
            "cro": "Chief Revenue Officer",
        }

        # Build per-role sprint prompts and query in parallel
        agent_outputs: dict[str, str] = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Generating {len(self.agents)} sprint plans in parallel...",
                total=None,
            )

            # Build prompts per role
            prompts = {}
            for role in self.agents:
                prompts[role] = SPRINT_PLAN_PROMPT.format(
                    sprint_number=self.sprint_number,
                    start_date=self.start_date or "TBD",
                    end_date=self.end_date or "TBD",
                    strategy_content=strategy_content,
                    role_title=role_titles.get(role, role.upper()),
                )

            # Query all agents in parallel using orchestrator
            perspectives = await orchestrator.query_agents_parallel(
                self.agents,  # type: ignore[arg-type]
                # Use first role's prompt as base — each agent's system prompt differentiates
                SPRINT_PLAN_PROMPT.format(
                    sprint_number=self.sprint_number,
                    start_date=self.start_date or "TBD",
                    end_date=self.end_date or "TBD",
                    strategy_content=strategy_content,
                    role_title="your role",
                ),
            )

            progress.update(task, description="[green]All sprint plans received")

        # Display and collect
        for p in perspectives:
            agent_outputs[p.role] = p.response
            self.console.print()
            self.console.print(
                Panel(
                    Markdown(p.response),
                    title=f"[bold]{p.name} — Sprint {self.sprint_number} Plan[/bold]",
                    border_style="blue",
                )
            )

        # Build dispatch manifest from all plans
        dispatch_manifest = self._build_dispatch_manifest(agent_outputs)

        self.console.print()
        self.console.print(
            Panel(
                Markdown(dispatch_manifest),
                title=f"[bold yellow]Dispatch Manifest — Sprint {self.sprint_number}[/bold yellow]",
                border_style="yellow",
            )
        )

        # Build result
        elapsed = (time.time() - start_time) / 60
        metrics = self.cost_tracker.get_daily_metrics()
        total_cost = metrics.total_cost

        markdown = self._format_markdown(
            perspectives, dispatch_manifest, elapsed, total_cost
        )

        if self.output_path:
            Path(self.output_path).write_text(markdown)
            self.console.print(f"\n[green]Output saved to:[/green] {self.output_path}")

        result = self._build_result(
            markdown_output=markdown,
            agent_outputs=agent_outputs,
            total_cost=total_cost,
            duration_minutes=elapsed,
        )

        # Write to Notion (Sprints DB)
        notion_url = await write_event_to_notion(
            result,
            extra_properties={
                "Sprint Goal": self.topic,
                "Status": _select_property("Not Started"),
            },
        )
        if notion_url:
            result.notion_url = notion_url
            self.console.print(f"[green]Notion page:[/green] {notion_url}")

        self.console.print(
            f"\n[dim]Sprint planning completed in {elapsed:.1f} minutes | "
            f"Cost: ${total_cost:.2f} | ID: {self.event_id}[/dim]\n"
        )

        return result

    def _build_dispatch_manifest(self, agent_outputs: dict[str, str]) -> str:
        """Extract sub-agent tasks from all exec plans into a dispatch manifest."""
        lines = [
            f"## Dispatch Manifest — Sprint {self.sprint_number}",
            "",
            "### Ready for Dispatch (Pending Chairman Approval)",
            "",
        ]

        for role, output in agent_outputs.items():
            # Extract lines that look like sub-agent tasks (checklist items)
            task_lines = [
                line.strip()
                for line in output.split("\n")
                if line.strip().startswith("- [ ]")
            ]
            if task_lines:
                lines.append(f"**{role.upper()} Delegates:**")
                lines.extend(task_lines)
                lines.append("")

        if len(lines) <= 4:
            lines.append(
                "*No structured sub-agent tasks extracted. "
                "Review individual plans for delegation opportunities.*"
            )

        return "\n".join(lines)

    def _format_markdown(self, perspectives, dispatch_manifest, elapsed, total_cost):
        lines = [
            f"# Sprint {self.sprint_number} Planning",
            "",
            f"**Goal:** {self.topic}",
            f"**Dates:** {self.start_date} to {self.end_date}",
            f"**Executives:** {', '.join(r.upper() for r in self.agents)}",
            f"**Event ID:** {self.event_id}",
            f"**Date:** {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Duration:** {elapsed:.1f} minutes",
            f"**Cost:** ${total_cost:.2f}",
            "",
            "---",
            "",
        ]

        for p in perspectives:
            lines.extend([
                f"## {p.name} — Sprint Plan",
                "",
                p.response,
                "",
                "---",
                "",
            ])

        lines.extend([dispatch_manifest, "", "---"])
        lines.append(f"*Generated by C-Suite Sprint Planning | {self.event_id}*")

        return "\n".join(lines)
