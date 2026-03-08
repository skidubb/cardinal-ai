"""P51: Wildcard Walk — includes one maximally orthogonal wildcard lens.

Same 6 stages as Walk Base, but select_promoted(include_wildcard=True)
ensures one high-cognitive-distance lens advances even if not top-ranked.
"""

from __future__ import annotations

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import trace_protocol
from protocols.walk_shared.schemas import WalkResult
from protocols.p49_walk_base.orchestrator import WalkBaseOrchestrator


class WildcardWalkOrchestrator(WalkBaseOrchestrator):
    """Wildcard variant — preserves one orthogonal wildcard lens."""

    variant_name: str = "wildcard"

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
            include_wildcard=True,  # Key difference: always include wildcard
        )

    @trace_protocol("p51_wildcard_walk")
    async def run(self, question: str) -> WalkResult:
        """Full 6-stage pipeline with wildcard preservation."""
        print(f"Wildcard Walk: {len(self._walkers)} walkers, wildcard=True")

        frame = await self._stage_frame(question)
        shallow_outputs = await self._stage_shallow_walk(question, frame)
        salience = await self._stage_salience(frame, shallow_outputs)
        deep_outputs = await self._stage_deep_walk(question, frame, salience, shallow_outputs)
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
