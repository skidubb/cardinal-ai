"""P50: Tournament Walk — cost-bounded walk, no cross-examination.

Skips Stage 4 (cross-exam) and defaults to fewer promoted agents (3).
~40% cheaper than Walk Base.
"""

from __future__ import annotations

import json
import logging

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.synthesis import SynthesisEngine
from protocols.walk_shared.prompts import SYNTHESIS_PROMPT
from protocols.walk_shared.schemas import (
    DeepWalkOutput,
    FrameArtifact,
    SalienceArtifact,
    ShallowWalkOutput,
    WalkResult,
    WalkSynthesis,
)
from protocols.walk_shared.selection import select_promoted
from protocols.p49_walk_base.orchestrator import WalkBaseOrchestrator
from protocols.llm import parse_json_object

_log = logging.getLogger(__name__)


class TournamentWalkOrchestrator(WalkBaseOrchestrator):
    """Tournament variant — no cross-examination, fewer promoted agents."""

    variant_name: str = "tournament"

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
        trace: bool = False,
        trace_path: str | None = None,
        promote_count: int = 3,
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

    @trace_protocol("p50_tournament_walk")
    async def run(self, question: str) -> WalkResult:
        """5-stage pipeline — skip cross-examination."""
        print(f"Tournament Walk: {len(self._walkers)} walkers, promote_count={self.promote_count}")

        frame = await self._stage_frame(question)
        shallow_outputs = await self._stage_shallow_walk(question, frame)
        salience = await self._stage_salience(frame, shallow_outputs)
        deep_outputs = await self._stage_deep_walk(question, frame, salience, shallow_outputs)

        # Skip cross-examination → go straight to synthesis
        synthesis, synthesis_text = await self._stage_synthesis(
            question, frame, shallow_outputs, salience, deep_outputs, [],
        )

        return WalkResult(
            question=question,
            protocol_variant=self.variant_name,
            frame=frame,
            shallow_outputs=shallow_outputs,
            salience=salience,
            deep_outputs=deep_outputs,
            cross_exam=[],  # No cross-exam in tournament
            synthesis=synthesis,
            synthesis_text=synthesis_text,
        )
