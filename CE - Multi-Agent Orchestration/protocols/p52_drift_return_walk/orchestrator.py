"""P52: Drift-and-Return Walk — separates reframing from solutioning.

Shallow walk uses a 'drift' prompt that explicitly says "forget the question."
Deep walk uses a 'return' prompt that forces explicit reconnection.
"""

from __future__ import annotations

import asyncio
import json
import logging

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import agent_complete, filter_exceptions, parse_json_object
from protocols.walk_shared.schemas import (
    FrameArtifact,
    ShallowWalkOutput,
    DeepWalkOutput,
    WalkResult,
)
from protocols.p49_walk_base.orchestrator import WalkBaseOrchestrator
from .prompts import DRIFT_SHALLOW_PROMPT, RETURN_DEEP_PROMPT

_log = logging.getLogger(__name__)


class DriftReturnWalkOrchestrator(WalkBaseOrchestrator):
    """Drift-and-Return variant — free exploration then forced reconnection."""

    variant_name: str = "drift_return"

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
        trace: bool = False,
        trace_path: str | None = None,
        promote_count: int = 4,
    ):
        super().__init__(
            agents=agents,
            thinking_model=thinking_model,
            orchestration_model=orchestration_model,
            thinking_budget=thinking_budget,
            trace=trace,
            trace_path=trace_path,
            promote_count=promote_count,
            include_wildcard=False,
        )

    @trace_protocol("p52_drift_return_walk")
    async def run(self, question: str) -> WalkResult:
        """Full 6-stage pipeline with drift/return prompt separation."""
        print(f"Drift-Return Walk: {len(self._walkers)} walkers")

        frame = await self._stage_frame(question)

        # Override: use drift prompt for shallow walk
        shallow_outputs = await self._stage_drift(question, frame)

        salience = await self._stage_salience(frame, shallow_outputs)

        # Override: use return prompt for deep walk
        deep_outputs = await self._stage_return(question, frame, salience, shallow_outputs)

        cross_exam = await self._stage_cross_examine(question, frame, deep_outputs)
        synthesis, synthesis_text = await self._stage_synthesis(
            question, frame, shallow_outputs, salience, deep_outputs, cross_exam,
        )

        return WalkResult(
            question=question,
            protocol_variant=self.variant_name,
            frame=frame,
            shallow_outputs=shallow_outputs,
            salience=salience,
            deep_outputs=deep_outputs,
            cross_exam=cross_exam,
            synthesis=synthesis,
            synthesis_text=synthesis_text,
        )

    async def _stage_drift(
        self, question: str, frame: FrameArtifact,
    ) -> list[ShallowWalkOutput]:
        """Stage 1 override: Drift — free exploration, forget the question."""
        print(f"Stage 1 (Drift): {len(self._walkers)} walkers exploring freely...")
        span = create_span("stage:drift", {"agent_count": len(self._walkers)})
        frame_json = json.dumps(frame.model_dump(), indent=2)

        async def drift_walker(walker: dict) -> ShallowWalkOutput:
            key = walker.get("_key", walker.get("name", "unknown"))
            meta = walker.get("walk_metadata", {})
            prompt = DRIFT_SHALLOW_PROMPT.format(
                question=question,
                frame_json=frame_json,
                agent_key=key,
                agent_name=walker["name"],
                lens_family=meta.get("lens_family", "general"),
            )
            raw = await agent_complete(
                agent=walker,
                fallback_model=self.balanced_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )
            data = parse_json_object(raw)
            return ShallowWalkOutput.model_validate(data)

        try:
            results = await asyncio.gather(
                *(drift_walker(w) for w in self._walkers),
                return_exceptions=True,
            )
            outputs = filter_exceptions(results, label="drift")
            end_span(span, output=f"{len(outputs)} drift outputs")
            return outputs
        except Exception:
            end_span(span, error="drift failed")
            raise

    async def _stage_return(
        self,
        question: str,
        frame: FrameArtifact,
        salience,
        shallow_outputs: list[ShallowWalkOutput],
    ) -> list[DeepWalkOutput]:
        """Stage 3 override: Return — force reconnection to the question."""
        from protocols.walk_shared.agents import WALK_AGENTS

        promoted_keys = salience.promoted_agents
        print(f"Stage 3 (Return): {len(promoted_keys)} promoted lenses returning...")
        span = create_span("stage:return", {"promoted_count": len(promoted_keys)})

        shallow_map = {s.agent_key: s for s in shallow_outputs}
        walker_map = {w.get("_key", w["name"]): w for w in self._walkers}
        frame_json = json.dumps(frame.model_dump(), indent=2)

        async def return_deep(agent_key: str) -> DeepWalkOutput:
            walker = walker_map.get(agent_key) or WALK_AGENTS.get(agent_key, {})
            shallow = shallow_map.get(agent_key)
            other_promoted = [
                shallow_map[k].model_dump()
                for k in promoted_keys
                if k != agent_key and k in shallow_map
            ]
            prompt = RETURN_DEEP_PROMPT.format(
                question=question,
                frame_json=frame_json,
                shallow_output_json=json.dumps(shallow.model_dump(), indent=2) if shallow else "{}",
                other_promoted_json=json.dumps(other_promoted, indent=2),
                agent_key=agent_key,
                agent_name=walker.get("name", agent_key),
            )
            raw = await agent_complete(
                agent=walker,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )
            data = parse_json_object(raw)
            return DeepWalkOutput.model_validate(data)

        try:
            results = await asyncio.gather(
                *(return_deep(key) for key in promoted_keys),
                return_exceptions=True,
            )
            outputs = filter_exceptions(results, label="return")
            end_span(span, output=f"{len(outputs)} return outputs")
            return outputs
        except Exception:
            end_span(span, error="return failed")
            raise
