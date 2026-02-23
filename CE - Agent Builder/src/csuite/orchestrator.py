"""
Multi-Agent Orchestrator for C-Suite agents.

Coordinates cross-functional analysis by invoking multiple agents and synthesizing
their perspectives into a holistic strategic recommendation.
"""

import asyncio
from dataclasses import dataclass
from typing import Literal

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.agents.base import BaseAgent
from csuite.agents.factory import create_agent
from csuite.config import get_settings
from csuite.session import Session, SessionManager


@dataclass
class AgentPerspective:
    """A perspective from a single agent."""

    role: str
    name: str
    response: str


AgentRole = Literal["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]


SYNTHESIS_SYSTEM_PROMPT = """You are a strategic synthesis advisor for a \
professional services firm. Your role is to integrate perspectives from \
different C-suite executives into a coherent strategic recommendation.

You have received input from multiple executive advisors:
- CEO: Strategic vision and market positioning
- CFO: Financial and economic analysis
- CTO: Technology and architecture considerations
- CMO: Marketing and positioning strategy
- COO: Operations and delivery perspective
- CPO: Product strategy and prioritization
- CRO: Revenue strategy, pipeline management, and GTM alignment

Your task is to:
1. Identify common themes and alignment across perspectives
2. Surface any tensions or trade-offs between recommendations
3. Synthesize a unified strategic recommendation
4. Prioritize actions considering all perspectives
5. Note any areas requiring further analysis or decision

Structure your synthesis as:

## Strategic Synthesis

### Executive Summary
[2-3 sentences capturing the unified recommendation]

### Aligned Perspectives
[Where the executives agree and why]

### Key Trade-offs
[Tensions between perspectives that require leadership decision]

### Integrated Recommendation
[Specific, actionable recommendations that balance all perspectives]

### Priority Actions
[Top 3-5 actions with owners and sequencing]

### Open Questions
[Issues requiring further analysis or executive decision]

Be direct, strategic, and actionable. The goal is to enable confident decision-making."""


class Orchestrator:
    """Orchestrates multi-agent analysis and synthesis."""

    AGENT_CLASSES: dict[AgentRole, type[BaseAgent]] = {
        "ceo": CEOAgent,
        "cfo": CFOAgent,
        "cto": CTOAgent,
        "cmo": CMOAgent,
        "coo": COOAgent,
        "cpo": CPOAgent,
        "cro": CROAgent,
    }

    def __init__(self):
        self.settings = get_settings()
        self.console = Console()
        self.session_manager = SessionManager()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def get_agent(self, role: AgentRole, session: Session | None = None) -> BaseAgent:
        """Get an agent instance by role."""
        return create_agent(role, session=session) if session else create_agent(role)

    async def query_agent(self, role: AgentRole, question: str) -> AgentPerspective:
        """Query a single agent and get their perspective."""
        agent = self.get_agent(role)
        response = await agent.chat(question)
        return AgentPerspective(
            role=role,
            name=agent.config.name,
            response=response,
        )

    async def query_agents_parallel(
        self,
        roles: list[AgentRole],
        question: str,
    ) -> list[AgentPerspective]:
        """Query multiple agents in parallel."""
        tasks = [self.query_agent(role, question) for role in roles]
        return await asyncio.gather(*tasks)

    def synthesize_perspectives(
        self,
        question: str,
        perspectives: list[AgentPerspective],
    ) -> tuple[str, object]:
        """Synthesize multiple agent perspectives into a unified recommendation.

        Returns:
            Tuple of (synthesis text, API usage object with input_tokens/output_tokens).
        """
        # Build the synthesis prompt
        perspectives_text = "\n\n".join(
            f"## {p.name} Perspective\n\n{p.response}" for p in perspectives
        )

        synthesis_prompt = f"""The following question was posed to the executive team:

**Question:** {question}

The following perspectives were provided:

{perspectives_text}

Please synthesize these perspectives into a unified strategic recommendation."""

        response = self.client.messages.create(
            model=self.settings.default_model,
            max_tokens=4096,
            temperature=0.7,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )

        return response.content[0].text, response.usage

    async def synthesize(
        self,
        question: str,
        roles: list[AgentRole] | None = None,
    ) -> str:
        """Run a cross-functional synthesis with multiple agents.

        Args:
            question: The strategic question to analyze
            roles: Which agents to consult (default: all six)

        Returns:
            Synthesized strategic recommendation
        """
        if roles is None:
            roles = ["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            # Query agents in parallel
            task = progress.add_task(
                f"[cyan]Consulting {len(roles)} executives...", total=None
            )
            perspectives = await self.query_agents_parallel(roles, question)
            progress.update(task, description="[green]Received all perspectives")

            # Display individual perspectives
            for p in perspectives:
                self.console.print()
                self.console.print(
                    Panel(
                        Markdown(p.response),
                        title=f"[bold]{p.name}[/bold]",
                        border_style="blue",
                    )
                )

            # Synthesize
            progress.update(task, description="[cyan]Synthesizing perspectives...")
            synthesis, _usage = self.synthesize_perspectives(question, perspectives)
            progress.update(task, description="[green]Synthesis complete")

        # Display synthesis
        self.console.print()
        self.console.print(
            Panel(
                Markdown(synthesis),
                title="[bold magenta]Strategic Synthesis[/bold magenta]",
                border_style="magenta",
            )
        )

        return synthesis

    def display_agent_response(self, perspective: AgentPerspective) -> None:
        """Display an agent's response with formatting."""
        self.console.print()
        self.console.print(
            Panel(
                Markdown(perspective.response),
                title=f"[bold blue]{perspective.name}[/bold blue]",
                border_style="blue",
            )
        )
