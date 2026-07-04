"""P01: Single Agent — one ServerAgent answers directly, full tool loop.

Second-from-bottom rung of the router ladder. Used when a question clearly
fits one expert role (CEO, CFO, CTO, etc.) and benefits from that role's
tools (web_search, etc.) but does NOT need multi-perspective synthesis or
debate.

Auto-select: if the caller passes no agent, P01 calls a cheap Haiku
classifier over the BUILTIN_AGENTS roster and picks the best-fit role
before running. Surfaces the selection in the result so the user knows
who answered and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import anthropic

from protocols.config import ORCHESTRATION_MODEL, THINKING_MODEL
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import agent_complete, extract_text, llm_complete, parse_json_object

from .prompts import CLASSIFIER_PROMPT


@dataclass
class SingleAgentResult:
    question: str
    agent_key: str = ""
    agent_name: str = ""
    response: str = ""
    # Auto-selection telemetry. Populated when the orchestrator chose the agent.
    # All None when the caller supplied an explicit agent.
    was_auto_selected: bool = False
    fit_score: float | None = None
    selection_reason: str = ""


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
            agents: Zero or one agent dict/ServerAgent. Empty list triggers
                    auto-selection from the built-in roster via a Haiku
                    classifier. With >1 entry, only agents[0] is used; extras
                    are ignored with a warning span note.
            thinking_model: Fallback model when the agent has no "model" field.
            orchestration_model: Model for the classifier (Haiku).
            thinking_budget: Token budget for extended thinking.
        """
        self.agents = list(agents or [])
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p01_single_agent")
    async def run(self, question: str) -> SingleAgentResult:
        """Execute the single-agent query, auto-selecting the agent if needed."""
        result = SingleAgentResult(question=question)

        # Stage 1 — Resolve the agent (explicit choice OR classifier pick).
        if not self.agents:
            span = create_span("stage:auto_select_agent", {})
            try:
                selection = await self._auto_select_agent(question)
                result.was_auto_selected = True
                result.fit_score = selection["fit_score"]
                result.selection_reason = selection["reason"]
                # Build the selected agent from the roster, using the SAME
                # mode the runner uses (production by default).
                from protocols.agents import build_agents

                built = build_agents([selection["agent_key"]])
                if not built:
                    raise ValueError(
                        f"classifier picked {selection['agent_key']!r} but "
                        "build_agents returned nothing — key may not exist"
                    )
                self.agents = built
                end_span(
                    span,
                    output=(
                        f"selected {selection['agent_key']} "
                        f"(fit={selection['fit_score']:.2f})"
                    ),
                )
            except Exception as e:
                end_span(span, error=f"auto_select failed: {e}")
                raise

        agent = self.agents[0]
        agent_name = (
            getattr(agent, "name", None)
            or (agent.get("name") if isinstance(agent, dict) else "unknown")
        )
        agent_key = (
            (agent.get("key") if isinstance(agent, dict) else None)
            or getattr(agent, "key", None)
            or agent_name
        )
        result.agent_key = str(agent_key)
        result.agent_name = str(agent_name)

        extras_note = (
            f"{len(self.agents) - 1} extra agent(s) ignored"
            if len(self.agents) > 1
            else ""
        )
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

    # ------------------------------------------------------------------
    # Auto-select: Haiku classifier over BUILTIN_AGENTS
    # ------------------------------------------------------------------

    async def _auto_select_agent(self, question: str) -> dict[str, Any]:
        """Return {'agent_key': str, 'fit_score': float, 'reason': str}."""
        from protocols.agents import BUILTIN_AGENTS

        roster_lines = []
        for key, spec in BUILTIN_AGENTS.items():
            name = spec.get("name", key)
            # First ~150 chars of the system prompt — enough to signal role.
            prompt_snippet = (spec.get("system_prompt", "") or "").replace("\n", " ")[:180]
            roster_lines.append(f"- {key}  ({name}) — {prompt_snippet}")
        roster_block = "\n".join(roster_lines)

        prompt = CLASSIFIER_PROMPT.format(
            question=question.strip(),
            roster_block=roster_block,
        )

        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            agent_name="p01_classifier",
        )
        raw = extract_text(resp)
        data = parse_json_object(raw)

        key = str(data.get("agent_key", "")).strip().lower()
        if not key or key not in BUILTIN_AGENTS:
            # Fall back to ceo — a reasonable generalist default.
            return {
                "agent_key": "ceo",
                "fit_score": 0.4,
                "reason": (
                    f"classifier returned unknown key {key!r}; falling back to ceo"
                ),
            }
        try:
            score = float(data.get("fit_score", 0.5))
        except (TypeError, ValueError):
            score = 0.5
        score = max(0.0, min(1.0, score))
        reason = str(data.get("reason", "")).strip() or "(no reason given)"
        return {"agent_key": key, "fit_score": score, "reason": reason}
