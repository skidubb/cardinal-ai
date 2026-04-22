"""P01: Single Agent — one ServerAgent answers directly, full tool loop.

Second-from-bottom rung of the router ladder. Used when a question clearly
fits one expert role (CEO, CFO, CTO, etc.) and benefits from that role's
tools (web_search, etc.) but does NOT need multi-perspective synthesis or
debate. If multiple perspectives matter, escalate to a multi-agent protocol.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import agent_complete

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


@dataclass
class SingleAgentResult:
    question: str
    agent_key: str = ""
    agent_name: str = ""
    response: str = ""


class SingleAgentOrchestrator:
    """Runs a question through exactly one ServerAgent with its full tool loop."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: List with exactly one agent dict or ServerAgent. Only agents[0]
                    is used; extras are ignored with a warning span note.
            thinking_model: Fallback model when the agent has no "model" field.
            orchestration_model: Unused. Accepted for signature consistency.
            thinking_budget: Token budget for extended thinking.
        """
        if not agents:
            raise ValueError("P01 requires exactly one agent (got none)")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p01_single_agent")
    async def run(self, question: str) -> SingleAgentResult:
        """Execute the single-agent query."""
        agent = self.agents[0]
        agent_name = getattr(agent, "name", None) or (agent.get("name") if isinstance(agent, dict) else "unknown")
        agent_key = (agent.get("key") if isinstance(agent, dict) else None) or getattr(agent, "key", None) or agent_name

        result = SingleAgentResult(
            question=question,
            agent_key=str(agent_key),
            agent_name=str(agent_name),
        )

        extras_note = f"{len(self.agents) - 1} extra agent(s) ignored" if len(self.agents) > 1 else ""
        span = create_span(
            "stage:single_agent_response",
            {"agent": str(agent_name), "extras": extras_note},
        )
        try:
            result.response = await agent_complete(
                agent,
                fallback_model=self.thinking_model,
                anthropic_client=self.client,
                thinking_budget=self.thinking_budget,
                max_tokens=self.thinking_budget + 4096,
                messages=[{"role": "user", "content": question}],
            )
            end_span(span, output="single agent response complete")
        except Exception:
            end_span(span, error="single_agent_response failed")
            raise

        return result
