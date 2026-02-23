"""
Multi-agent evaluation benchmark.

Runs the same strategic question through 5 execution modes and collects
outputs, costs, durations, and structural trace metrics for blind comparison.
"""

from __future__ import annotations

import time
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.agents.base import BaseAgent
from csuite.config import get_settings
from csuite.debate import DebateOrchestrator
from csuite.orchestrator import AgentRole, Orchestrator
from csuite.tools.cost_tracker import CostTracker, UsageRecord
from csuite.tracing.graph import ActionType, CausalGraph


class _CostAccumulator(CostTracker):
    """CostTracker subclass that accumulates costs in memory for benchmark isolation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_cost = 0.0
        self._run_input_tokens = 0
        self._run_output_tokens = 0

    def log_usage(  # type: ignore[override]
        self,
        agent: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        **kwargs,
    ) -> UsageRecord:
        record = super().log_usage(
            agent=agent, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            **kwargs,
        )
        self._run_cost += record.total_cost
        self._run_input_tokens += record.input_tokens
        self._run_output_tokens += record.output_tokens
        return record

    @property
    def run_totals(self) -> tuple[float, int, int]:
        return self._run_cost, self._run_input_tokens, self._run_output_tokens

AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "cto": CTOAgent,
    "cmo": CMOAgent,
    "coo": COOAgent,
    "cpo": CPOAgent,
    "cro": CROAgent,
}

BENCHMARK_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "pricing",
        "text": (
            "Should Cardinal Element offer a free 30-minute discovery call as a "
            "top-of-funnel lead magnet, or would that devalue our premium positioning?"
        ),
        "expected_tensions": ["cfo", "cmo"],
    },
    {
        "id": "plg",
        "text": (
            "Should we launch a self-serve PLG tier alongside our high-touch "
            "consulting model? What are the risks to our brand and unit economics?"
        ),
        "expected_tensions": ["cpo", "cfo", "cro"],
    },
    {
        "id": "capacity",
        "text": (
            "We have capacity for 2 more concurrent engagements. Should we hire a "
            "senior consultant or invest that budget in AI automation to scale delivery?"
        ),
        "expected_tensions": ["coo", "cto", "cfo"],
    },
    {
        "id": "competitive",
        "text": (
            "A competitor just raised $20M and is offering free audits to capture "
            "market share. How should we respond without entering a race to the bottom?"
        ),
        "expected_tensions": ["ceo", "cmo", "cfo"],
    },
    {
        "id": "open_source",
        "text": (
            "Should we open-source our audit framework to build community and "
            "thought leadership, or keep it proprietary as a competitive moat?"
        ),
        "expected_tensions": ["cto", "cpo", "ceo"],
    },
    {
        "id": "client_concentration",
        "text": (
            "Our largest client represents 40% of revenue and just asked for a 25% "
            "discount on their renewal. They're hinting they'll leave if we don't match "
            "a competitor's pricing. What do we do?"
        ),
        "expected_tensions": ["cro", "cfo", "ceo"],
    },
    {
        "id": "conference_spend",
        "text": (
            "We've been invited to sponsor a major industry conference for $50K. Our "
            "entire Q1 marketing budget is $80K. Should we go all-in on this event or "
            "spread the budget across digital channels?"
        ),
        "expected_tensions": ["cmo", "cfo", "ceo"],
    },
    {
        "id": "delivery_overrun",
        "text": (
            "Three of our five engagements are running 2-3 weeks behind schedule. Do "
            "we eat the overrun costs, renegotiate timelines with clients, or bring in "
            "subcontractors at a margin hit?"
        ),
        "expected_tensions": ["coo", "cfo", "cro"],
    },
    {
        "id": "enterprise_opp",
        "text": (
            "A Fortune 500 company wants to hire us for a $500K engagement, but it's "
            "outside our ICP — they're a 2,000-person enterprise, not a $5-40M operator. "
            "Do we take it?"
        ),
        "expected_tensions": ["ceo", "cpo", "coo"],
    },
    {
        "id": "margin_vs_speed",
        "text": (
            "Our top-performing agent workflow takes 45 minutes and costs $12 in API "
            "fees to produce a deliverable we charge $2,500 for. A competitor is offering "
            "a similar deliverable for $500 using a simpler approach. Should we cut our "
            "price, improve our speed, or double down on premium?"
        ),
        "expected_tensions": ["cfo", "cto", "cpo"],
    },
    {
        "id": "conversion_vs_volume",
        "text": (
            "We're generating 200 inbound leads per month from content but only "
            "converting 3%. Should we invest in improving conversion (better sales "
            "process, faster follow-up) or in generating more volume (more content, "
            "paid ads)?"
        ),
        "expected_tensions": ["cro", "cmo", "coo"],
    },
    {
        "id": "talent_poach",
        "text": (
            "A key employee at a client company has become our internal champion and is "
            "asking to join us as a full-time hire. We have a no-poaching policy in our "
            "contracts. They're willing to wait 6 months. What's the right move?"
        ),
        "expected_tensions": ["ceo", "coo", "cfo"],
    },
    {
        "id": "pe_investment",
        "text": (
            "We've been approached by a private equity firm interested in investing $2M "
            "for 20% equity. The money would let us hire 3 senior consultants and build "
            "a proprietary platform. Should we take it?"
        ),
        "expected_tensions": ["ceo", "cfo", "cto"],
    },
    {
        "id": "nps_drop",
        "text": (
            "Our quarterly NPS just dropped from 72 to 54. Exit interviews suggest "
            "clients love the strategic insights but hate the implementation support. "
            "Do we fix implementation, drop it from our offering, or partner with an "
            "implementation firm?"
        ),
        "expected_tensions": ["cpo", "coo", "cro"],
    },
    {
        "id": "acquisition",
        "text": (
            "We have the opportunity to acquire a struggling 8-person consulting firm "
            "in an adjacent market for $400K. They have 12 active clients but negative "
            "EBITDA. Is this a growth accelerator or a distraction?"
        ),
        "expected_tensions": ["ceo", "cfo", "coo"],
    },
]

ALL_ROLE_SYSTEM_PROMPT = """You are a unified executive advisor who combines \
the perspectives of all seven C-suite roles for a professional services / \
consulting firm:

- **CEO**: Strategic vision, competitive positioning, market dynamics, growth strategy
- **CFO**: Unit economics, cash flow, pricing models, financial risk
- **CTO**: Technology architecture, build vs. buy, AI/automation, security
- **CMO**: Brand positioning, demand generation, thought leadership, competitive messaging
- **COO**: Resource planning, delivery excellence, process optimization, capacity management
- **CPO**: Service design, product-market fit, roadmap prioritization, client experience
- **CRO**: Revenue strategy, pipeline management, GTM alignment, sales methodology

When answering, explicitly consider ALL seven perspectives. Surface genuine \
tensions between them. Provide a unified recommendation that acknowledges \
trade-offs.

Be specific, actionable, and grounded in the realities of running a \
$5-40M ARR professional services firm with 20-150 employees."""


class ModeResult(BaseModel):
    """Result from running a single question through one execution mode."""

    mode: str
    question_id: str
    output_text: str
    cost: float = 0.0
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    trace_metrics: dict[str, Any] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):
    """Aggregated results from running all questions through all modes."""

    results: dict[str, dict[str, ModeResult]] = Field(default_factory=dict)
    """Keyed by question_id -> mode -> ModeResult."""


class BenchmarkRunner:
    """Runs a question through all 5 modes, collects outputs + costs."""

    def __init__(
        self,
        roles: list[str] | None = None,
        rounds: int = 2,
        silent: bool = True,
        disable_tools: bool = False,
    ):
        self.roles: list[str] = roles or ["cfo", "cmo", "cto"]
        self.rounds = rounds
        self.silent = silent
        self.settings = get_settings()
        self._original_tools_enabled = self.settings.tools_enabled
        if disable_tools:
            self.settings.tools_enabled = False

    async def run_single(self, question: str, question_id: str, role: str = "ceo") -> ModeResult:
        """Mode A: Single agent answers the full question."""
        tracker = _CostAccumulator()
        agent = AGENT_CLASSES[role](cost_tracker=tracker)
        start = time.time()
        output = await agent.chat(question)
        elapsed = time.time() - start
        cost, in_tok, out_tok = tracker.run_totals
        return ModeResult(
            mode="single",
            question_id=question_id,
            output_text=output,
            cost=cost,
            duration_seconds=elapsed,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    async def run_single_with_context(self, question: str, question_id: str) -> ModeResult:
        """Mode B: Single Opus call with all-role system prompt."""
        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        start = time.time()
        response = client.messages.create(
            model=self.settings.default_model,
            max_tokens=4096,
            temperature=0.7,
            system=ALL_ROLE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        elapsed = time.time() - start
        output = response.content[0].text
        cost = _estimate_cost(
            response.model, response.usage.input_tokens, response.usage.output_tokens
        )
        return ModeResult(
            mode="context",
            question_id=question_id,
            output_text=output,
            cost=cost,
            duration_seconds=elapsed,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def run_synthesize(self, question: str, question_id: str) -> ModeResult:
        """Mode C: Parallel agents + single-pass synthesis."""
        orchestrator = Orchestrator()
        start = time.time()

        agent_roles: list[AgentRole] = self.roles  # type: ignore[assignment]

        # Run parallel queries
        perspectives = await orchestrator.query_agents_parallel(agent_roles, question)
        synthesis_text, usage = orchestrator.synthesize_perspectives(question, perspectives)

        elapsed = time.time() - start
        # Rough cost from usage (usage is anthropic.types.Usage but typed as object)
        input_tok = getattr(usage, "input_tokens", 0)
        output_tok = getattr(usage, "output_tokens", 0)
        cost = _estimate_cost(self.settings.default_model, input_tok, output_tok)

        return ModeResult(
            mode="synthesize",
            question_id=question_id,
            output_text=synthesis_text,
            cost=cost,
            duration_seconds=elapsed,
            input_tokens=input_tok,
            output_tokens=output_tok,
        )

    async def run_debate(self, question: str, question_id: str) -> ModeResult:
        """Mode D: Multi-round debate with rebuttals."""
        tracker = _CostAccumulator()
        graph = CausalGraph()
        orch = DebateOrchestrator(cost_tracker=tracker)
        # Suppress Rich output
        if self.silent:
            from rich.console import Console
            orch.console = Console(quiet=True)

        start = time.time()
        session = await orch.run_debate(
            question, roles=self.roles, total_rounds=self.rounds, causal_graph=graph,
        )
        elapsed = time.time() - start
        cost, in_tok, out_tok = tracker.run_totals

        revisions = sum(
            1 for n in graph.nodes.values() if n.action_type == ActionType.REVISE
        )
        constraints = sum(
            1 for n in graph.nodes.values() if n.action_type == ActionType.CONSTRAIN
        )

        return ModeResult(
            mode="debate",
            question_id=question_id,
            output_text=session.synthesis or "",
            cost=cost,
            duration_seconds=elapsed,
            input_tokens=in_tok,
            output_tokens=out_tok,
            trace_metrics={
                "node_count": graph.node_count(),
                "revision_count": revisions,
                "constraint_count": constraints,
            },
        )

    async def run_negotiate(self, question: str, question_id: str) -> ModeResult:
        """Mode E: Debate + constraint extraction/propagation."""
        tracker = _CostAccumulator()
        graph = CausalGraph()
        orch = DebateOrchestrator(cost_tracker=tracker)
        if self.silent:
            from rich.console import Console
            orch.console = Console(quiet=True)

        start = time.time()
        session = await orch.run_negotiation(
            question, roles=self.roles, total_rounds=self.rounds, causal_graph=graph,
        )
        elapsed = time.time() - start
        cost, in_tok, out_tok = tracker.run_totals

        revisions = sum(
            1 for n in graph.nodes.values() if n.action_type == ActionType.REVISE
        )
        constraints = sum(
            1 for n in graph.nodes.values() if n.action_type == ActionType.CONSTRAIN
        )

        return ModeResult(
            mode="negotiate",
            question_id=question_id,
            output_text=session.synthesis or "",
            cost=cost,
            duration_seconds=elapsed,
            input_tokens=in_tok,
            output_tokens=out_tok,
            trace_metrics={
                "node_count": graph.node_count(),
                "revision_count": revisions,
                "constraint_count": constraints,
            },
        )

    async def run_all_modes(
        self,
        question: str,
        question_id: str,
        modes: list[str] | None = None,
    ) -> dict[str, ModeResult]:
        """Run a question through selected modes sequentially."""
        modes = modes or ["single", "context", "synthesize", "debate", "negotiate"]
        runners = {
            "single": lambda: self.run_single(question, question_id),
            "context": lambda: self.run_single_with_context(question, question_id),
            "synthesize": lambda: self.run_synthesize(question, question_id),
            "debate": lambda: self.run_debate(question, question_id),
            "negotiate": lambda: self.run_negotiate(question, question_id),
        }
        results: dict[str, ModeResult] = {}
        for mode in modes:
            if mode in runners:
                results[mode] = await runners[mode]()
        return results

    async def run_full_benchmark(
        self,
        num_questions: int = 5,
        modes: list[str] | None = None,
    ) -> BenchmarkResult:
        """Run all questions through all modes."""
        questions = BENCHMARK_QUESTIONS[:num_questions]
        benchmark = BenchmarkResult()

        for q in questions:
            mode_results = await self.run_all_modes(q["text"], q["id"], modes)
            benchmark.results[q["id"]] = mode_results

        return benchmark

    def restore_settings(self) -> None:
        """Restore tools_enabled to its original value after benchmark run."""
        self.settings.tools_enabled = self._original_tools_enabled


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in dollars using Feb 2026 Anthropic pricing."""
    pricing = {
        "claude-opus-4-6": (5.0, 25.0),
        "claude-sonnet-4-5-20250929": (3.0, 15.0),
        "claude-haiku-4-5-20251001": (1.0, 5.0),
    }
    # Match by prefix for model variants
    rates = (5.0, 25.0)  # default to opus
    for key, val in pricing.items():
        if key in model or model in key:
            rates = val
            break
    return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000
