"""P53: Stigmergic Coordination — decentralized trace-field orchestrator.

Novel decentralized-loop protocol. Agents drop typed traces on locations in
a shared field. Later agents read the accumulated (and decayed) field and
drop their own traces. The final report is the mechanically-harvested trace
field grouped by type and sorted by cumulative strength. No central
synthesizer merges opinions.

Pure helpers (parse/decay/harvest/format) live in `field.py` so they can be
imported and tested without the litellm/anthropic import cascade.
"""

from __future__ import annotations

import asyncio

import anthropic

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete
from protocols.scoping import scoped_prompt

from .field import (
    DECAY_PER_WAVE,
    DEFAULT_TOP_N_PER_TYPE,
    DEFAULT_WAVES,
    LocationSummary,
    StigmergyResult,
    TRACE_TYPES,
    Trace,
    format_trace_field,
    harvest_field,
    parse_traces,
)
from .prompts import initial_wave_prompt, reaction_wave_prompt


__all__ = [
    "StigmergyOrchestrator",
    "StigmergyResult",
    "Trace",
    "LocationSummary",
    "DECAY_PER_WAVE",
    "TRACE_TYPES",
    "DEFAULT_WAVES",
    "DEFAULT_TOP_N_PER_TYPE",
    # Re-export helpers for backward compat with test imports.
    "parse_traces",
    "format_trace_field",
    "harvest_field",
]


class StigmergyOrchestrator:
    """Stigmergic coordination — no central synthesizer."""

    def __init__(
        self,
        agents: list[dict] | None = None,
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        waves: int = DEFAULT_WAVES,
        top_n_per_type: int = DEFAULT_TOP_N_PER_TYPE,
        thinking_budget: int = 4_000,
    ) -> None:
        self.agents = agents or []
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.waves = max(1, waves)
        self.top_n_per_type = max(1, top_n_per_type)
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p53_stigmergy")
    async def run(self, question: str) -> StigmergyResult:
        result = StigmergyResult(
            question=question,
            waves=self.waves,
            agents=[a.get("name", "?") for a in self.agents],
        )
        if not self.agents:
            return result

        span = create_span("stage:wave_1_seed", {"agents": len(self.agents)})
        try:
            wave_1 = await self._run_wave(question, wave_number=1, prior_traces=[])
            result.all_traces.extend(wave_1)
            end_span(span, output=f"{len(wave_1)} traces deposited")
        except Exception:
            end_span(span, error="wave_1 failed")
            raise

        for wave_number in range(2, self.waves + 1):
            span = create_span(
                f"stage:wave_{wave_number}_reaction",
                {"agents": len(self.agents), "field_size": len(result.all_traces)},
            )
            try:
                wave = await self._run_wave(
                    question, wave_number=wave_number, prior_traces=result.all_traces
                )
                result.all_traces.extend(wave)
                end_span(span, output=f"{len(wave)} new traces deposited")
            except Exception:
                end_span(span, error=f"wave_{wave_number} failed")
                raise

        span = create_span("stage:harvest", {"total_traces": len(result.all_traces)})
        try:
            result.by_type = harvest_field(
                result.all_traces, top_n_per_type=self.top_n_per_type
            )
            end_span(
                span,
                output=f"{sum(len(v) for v in result.by_type.values())} location-summaries",
            )
        except Exception:
            end_span(span, error="harvest failed")
            raise

        return result

    async def _run_wave(
        self,
        question: str,
        wave_number: int,
        prior_traces: list[Trace],
    ) -> list[Trace]:
        """One wave: every agent (parallel) drops 2-4 traces on the field."""
        trace_field = format_trace_field(prior_traces, current_wave=wave_number)

        async def _one(agent: dict) -> list[Trace]:
            agent_name = agent.get("name", "Agent")
            agent_role = agent.get("system_prompt", f"a {agent_name}").split(".")[0]
            if wave_number == 1:
                base_prompt = initial_wave_prompt(question, agent_name, agent_role)
            else:
                base_prompt = reaction_wave_prompt(
                    question, agent_name, agent_role, trace_field, wave_number
                )
            prompt = scoped_prompt(agent, base_prompt)
            resp = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent_name,
            )
            return parse_traces(extract_text(resp), author=agent_name, wave=wave_number)

        results = await asyncio.gather(*(_one(a) for a in self.agents), return_exceptions=True)
        traces: list[Trace] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            traces.extend(r)
        return traces
