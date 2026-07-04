"""P49: Walk Base — 6-stage cognitive walk orchestrator.

Stage 0: Frame (L4, single) → Stage 1: Shallow Walk (L3, parallel) →
Stage 2: Salience (L2, single) → Stage 3: Deep Walk (L4, parallel) →
Stage 4: Cross-Examination (L3, parallel) → Stage 5: Synthesis (L4, single)
"""

from __future__ import annotations

import asyncio
import json
import logging

from pathlib import Path
from typing import Any

from protocols.config import (
    BALANCED_MODEL,
    ORCHESTRATION_MODEL,
    THINKING_MODEL,
)
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import (
    agent_complete,
    filter_exceptions,
    parse_json_object,
)
from protocols.synthesis import SynthesisEngine
from protocols.tracing import make_client
from protocols.walk_shared.agents import WALK_AGENTS
from protocols.walk_shared.prompts import (
    COLLISION_SYNTHESIS_PROMPT,
    CROSS_EXAM_PROMPT,
    DEEP_WALK_PROMPT,
    FRAME_PROMPT,
    PROVOCATION_PROMPT,
    SHALLOW_WALK_PROMPT,
    SYNTHESIS_PROMPT,
)
from protocols.walk_shared.schemas import (
    CollisionFusion,
    CrossExamEntry,
    DeepWalkOutput,
    FrameArtifact,
    SalienceArtifact,
    ShallowWalkOutput,
    WalkProvocation,
    WalkResult,
    WalkSynthesis,
)
from protocols.walk_shared.selection import (
    build_collision_pairings,
    build_cross_exam_pairings,
    score_salience,
    select_promoted,
)

_log = logging.getLogger(__name__)


class WalkBaseOrchestrator:
    """Runs the 6-stage Walk Base protocol with cognitive lens agents."""

    variant_name: str = "walk_base"

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
        trace: bool = False,
        trace_path: str | None = None,
        promote_count: int = 4,
        include_wildcard: bool = False,
    ):
        if not agents:
            raise ValueError("At least one agent is required")

        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.balanced_model = BALANCED_MODEL
        self.thinking_budget = thinking_budget
        self.promote_count = promote_count
        self.include_wildcard = include_wildcard
        self.client: Any = make_client(
            protocol_id="p49_walk_base",
            trace=trace,
            trace_path=Path(trace_path) if trace_path else None,
        )

        # Separate walk agents by role
        self._walkers: list[dict] = []
        self._framer: dict | None = None
        self._judge: dict | None = None
        self._synthesizer: dict | None = None
        self._resolve_agents()

    def _resolve_agents(self) -> None:
        """Partition agents into framer, judge, synthesizer, and walkers."""
        for agent in self.agents:
            key = agent.get("_key", "")
            meta = agent.get("walk_metadata", {})
            mode = meta.get("default_depth_mode", "both")

            if key == "walk-framer" or mode == "frame":
                self._framer = agent
            elif key == "walk-salience-judge" or mode == "score":
                self._judge = agent
            elif key == "walk-synthesizer" or mode == "synthesize":
                self._synthesizer = agent
            else:
                self._walkers.append(agent)

        # Fall back to walk_shared agents if not provided
        if self._framer is None:
            self._framer = {**WALK_AGENTS["walk-framer"], "_key": "walk-framer"}  # type: ignore[assignment]
        if self._judge is None:
            self._judge = {
                **WALK_AGENTS["walk-salience-judge"],
                "_key": "walk-salience-judge",
            }
        if self._synthesizer is None:
            self._synthesizer = {
                **WALK_AGENTS["walk-synthesizer"],
                "_key": "walk-synthesizer",
            }

        # If no walkers provided, use all non-meta walk agents
        if not self._walkers:
            for key, agent_def in WALK_AGENTS.items():
                meta = agent_def.get("walk_metadata", {})
                if meta.get("default_depth_mode") in ("both", "shallow", "deep"):
                    self._walkers.append({**agent_def, "_key": key})

    @trace_protocol("p49_walk_base")
    async def run(self, question: str) -> WalkResult:
        """Execute the full 6-stage Walk Base protocol."""
        print(
            f"Walk Base: {len(self._walkers)} walkers, promote_count={self.promote_count}"
        )

        # Stage 0: Frame
        frame = await self._stage_frame(question)

        # Stage 1: Shallow Walk (parallel)
        shallow_outputs = await self._stage_shallow_walk(question, frame)

        # Stage 2: Salience
        salience = await self._stage_salience(frame, shallow_outputs)

        # Stage 3: Deep Walk (parallel, promoted only)
        deep_outputs = await self._stage_deep_walk(
            question, frame, salience, shallow_outputs
        )

        # Stage 4: Cross-Examination (parallel pairings)
        cross_exam = await self._stage_cross_examine(question, frame, deep_outputs)

        # Stage 4.5: Collision Synthesis (generative fusion across core + periphery)
        collisions = await self._stage_collision_synthesis(
            frame,
            salience,
            deep_outputs,
            shallow_outputs,
        )

        # Stage 5: Synthesis
        synthesis, synthesis_text = await self._stage_synthesis(
            question,
            frame,
            shallow_outputs,
            salience,
            deep_outputs,
            cross_exam,
            collisions,
        )

        # Stage 6: Provocation (walk-back-to-desk bridge)
        provocation = await self._stage_provocation(
            frame,
            shallow_outputs,
            deep_outputs,
            collisions,
        )

        return WalkResult(
            question=question,
            protocol_variant=self.variant_name,
            frame=frame,
            shallow_outputs=shallow_outputs,
            salience=salience,
            deep_outputs=deep_outputs,
            cross_exam=cross_exam,
            collisions=collisions,
            synthesis=synthesis,
            synthesis_text=synthesis_text,
            provocation=provocation,
        )

    # ── Stage implementations ─────────────────────────────────────────────

    async def _stage_frame(self, question: str) -> FrameArtifact:
        """Stage 0: Problem Framer decomposes the question (L4)."""
        print("Stage 0: Framing problem...")
        span = create_span("stage:frame", {})
        try:
            assert self._framer is not None, "Problem Framer agent not resolved"
            prompt = FRAME_PROMPT.format(question=question)
            raw = await agent_complete(
                agent=self._framer,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )
            data = parse_json_object(raw)
            frame = FrameArtifact.model_validate(data)
            end_span(span, output=f"frame: {len(frame.constraints)} constraints")
            return frame
        except Exception:
            end_span(span, error="frame failed")
            raise

    async def _stage_shallow_walk(
        self,
        question: str,
        frame: FrameArtifact,
    ) -> list[ShallowWalkOutput]:
        """Stage 1: All walkers produce shallow reframings in parallel (L3)."""
        print(f"Stage 1: Shallow walk with {len(self._walkers)} walkers...")
        span = create_span("stage:shallow_walk", {"agent_count": len(self._walkers)})
        frame_json = json.dumps(frame.model_dump(), indent=2)

        async def query_walker(walker: dict) -> ShallowWalkOutput:
            key = walker.get("_key", walker.get("name", "unknown"))
            meta = walker.get("walk_metadata", {})
            prompt = SHALLOW_WALK_PROMPT.format(
                question=question,
                frame_json=frame_json,
                agent_key=key,
                agent_name=walker["name"],
                lens_family=meta.get("lens_family", "general"),
                lens_mandate=meta.get(
                    "lens_mandate", "Apply your lens to explore this domain."
                ),
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
                *(query_walker(w) for w in self._walkers),
                return_exceptions=True,
            )
            outputs = filter_exceptions(results, label="shallow_walk")
            end_span(span, output=f"{len(outputs)} shallow outputs")
            return outputs
        except Exception:
            end_span(span, error="shallow_walk failed")
            raise

    async def _stage_salience(
        self,
        frame: FrameArtifact,
        shallow_outputs: list[ShallowWalkOutput],
    ) -> SalienceArtifact:
        """Stage 2: Salience Judge scores all shallow outputs (L2)."""
        print("Stage 2: Scoring salience...")
        span = create_span("stage:salience", {"output_count": len(shallow_outputs)})
        try:
            salience = await score_salience(
                shallow_outputs=shallow_outputs,
                frame=frame,
                client=self.client,
                model=self.orchestration_model,
            )
            # Override promoted agents with our selection logic
            promoted = select_promoted(
                salience.ranked_outputs,
                top_n=self.promote_count,
                include_wildcard=self.include_wildcard,
            )
            salience.promoted_agents = promoted
            end_span(span, output=f"promoted {len(promoted)} agents")
            return salience
        except Exception:
            end_span(span, error="salience failed")
            raise

    async def _stage_deep_walk(
        self,
        question: str,
        frame: FrameArtifact,
        salience: SalienceArtifact,
        shallow_outputs: list[ShallowWalkOutput],
    ) -> list[DeepWalkOutput]:
        """Stage 3: Promoted walkers do deep analysis in parallel (L4)."""
        promoted_keys = salience.promoted_agents
        print(f"Stage 3: Deep walk with {len(promoted_keys)} promoted lenses...")
        span = create_span("stage:deep_walk", {"promoted_count": len(promoted_keys)})

        # Build lookup maps
        shallow_map = {s.agent_key: s for s in shallow_outputs}
        walker_map = {w.get("_key", w["name"]): w for w in self._walkers}
        frame_json = json.dumps(frame.model_dump(), indent=2)

        async def query_deep(agent_key: str) -> DeepWalkOutput:
            walker = walker_map.get(agent_key) or WALK_AGENTS.get(agent_key, {})
            shallow = shallow_map.get(agent_key)
            other_promoted = [
                shallow_map[k].model_dump()
                for k in promoted_keys
                if k != agent_key and k in shallow_map
            ]
            prompt = DEEP_WALK_PROMPT.format(
                question=question,
                frame_json=frame_json,
                shallow_output_json=json.dumps(shallow.model_dump(), indent=2)
                if shallow
                else "{}",
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
                *(query_deep(key) for key in promoted_keys),
                return_exceptions=True,
            )
            outputs = filter_exceptions(results, label="deep_walk")
            end_span(span, output=f"{len(outputs)} deep outputs")
            return outputs
        except Exception:
            end_span(span, error="deep_walk failed")
            raise

    async def _stage_cross_examine(
        self,
        question: str,
        frame: FrameArtifact,
        deep_outputs: list[DeepWalkOutput],
    ) -> list[CrossExamEntry]:
        """Stage 4: Cross-examination between promoted lenses (L3)."""
        deep_map = {d.agent_key: d for d in deep_outputs}
        pairings = build_cross_exam_pairings(list(deep_map.keys()))
        print(f"Stage 4: Cross-examination with {len(pairings)} pairings...")
        span = create_span("stage:cross_exam", {"pairing_count": len(pairings)})

        async def examine(challenger_key: str, target_key: str) -> CrossExamEntry:
            challenger_deep = deep_map.get(challenger_key)
            target_deep = deep_map.get(target_key)
            prompt = CROSS_EXAM_PROMPT.format(
                challenger_key=challenger_key,
                target_key=target_key,
                target_deep_output_json=json.dumps(target_deep.model_dump(), indent=2)
                if target_deep
                else "{}",
                challenger_deep_output_json=json.dumps(
                    challenger_deep.model_dump(), indent=2
                )
                if challenger_deep
                else "{}",
            )
            walker = next(
                (w for w in self._walkers if w.get("_key") == challenger_key),
                {
                    "name": challenger_key,
                    "system_prompt": "You are a critical examiner.",
                },
            )
            raw = await agent_complete(
                agent=walker,
                fallback_model=self.balanced_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )
            data = parse_json_object(raw)
            return CrossExamEntry.model_validate(data)

        try:
            results = await asyncio.gather(
                *(examine(c, t) for c, t in pairings),
                return_exceptions=True,
            )
            entries = filter_exceptions(results, label="cross_exam")
            end_span(span, output=f"{len(entries)} cross-exam entries")
            return entries
        except Exception:
            end_span(span, error="cross_exam failed")
            raise

    async def _stage_collision_synthesis(
        self,
        frame: FrameArtifact,
        salience: SalienceArtifact,
        deep_outputs: list[DeepWalkOutput],
        shallow_outputs: list[ShallowWalkOutput],
    ) -> list[CollisionFusion]:
        """Stage 4.5: Generative fusion across core and periphery lenses (L4).

        Pairs promoted lenses with each other AND with high-scoring periphery
        lenses (composite 6-7 that weren't promoted). For each pair, asks what
        third idea emerges that neither lens stated and whether it dissolves a
        Frame tension. Filters to high-signal fusions (composite >= 7).
        """
        pairings = build_collision_pairings(
            promoted=salience.promoted_agents,
            ranked=salience.ranked_outputs,
        )
        print(f"Stage 4.5: Collision synthesis with {len(pairings)} pairings...")
        span = create_span(
            "stage:collision_synthesis", {"pairing_count": len(pairings)}
        )

        deep_map = {d.agent_key: d for d in deep_outputs}
        shallow_map = {s.agent_key: s for s in shallow_outputs}
        frame_json = json.dumps(frame.model_dump(), indent=2)

        async def fuse_one(
            a_key: str, b_key: str, ptype: str
        ) -> CollisionFusion | None:
            a_src = deep_map.get(a_key) or shallow_map.get(a_key)
            b_src = deep_map.get(b_key) or shallow_map.get(b_key)
            if a_src is None or b_src is None:
                return None
            prompt = COLLISION_SYNTHESIS_PROMPT.format(
                lens_a_key=a_key,
                lens_b_key=b_key,
                pairing_type=ptype,
                lens_a_json=json.dumps(a_src.model_dump(), indent=2),
                lens_b_json=json.dumps(b_src.model_dump(), indent=2),
                frame_json=frame_json,
            )
            assert self._synthesizer is not None
            raw = await agent_complete(
                agent=self._synthesizer,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )
            data = parse_json_object(raw)
            surprise = float(data.get("surprise_score", 5))
            resolution = float(data.get("resolution_power", 5))
            data["surprise_score"] = surprise
            data["resolution_power"] = resolution
            data["composite"] = 0.5 * surprise + 0.5 * resolution
            return CollisionFusion.model_validate(data)

        try:
            results = await asyncio.gather(
                *(fuse_one(a, b, p) for a, b, p in pairings),
                return_exceptions=True,
            )
            fusions = [f for f in filter_exceptions(results, label="collision") if f]
            # Keep only genuine, high-signal fusions
            high_signal = sorted(
                [f for f in fusions if f.emergent_idea and f.composite >= 7.0],
                key=lambda f: f.composite,
                reverse=True,
            )
            end_span(
                span, output=f"{len(high_signal)}/{len(fusions)} high-signal fusions"
            )
            return high_signal
        except Exception:
            end_span(span, error="collision_synthesis failed")
            raise

    async def _stage_synthesis(
        self,
        question: str,
        frame: FrameArtifact,
        shallow_outputs: list[ShallowWalkOutput],
        salience: SalienceArtifact,
        deep_outputs: list[DeepWalkOutput],
        cross_exam: list[CrossExamEntry],
        collisions: list[CollisionFusion] | None = None,
    ) -> tuple[WalkSynthesis | None, str]:
        """Stage 5: Synthesize all walk outputs (L4)."""
        print("Stage 5: Synthesizing...")
        span = create_span("stage:synthesis", {})

        prompt = SYNTHESIS_PROMPT.format(
            question=question,
            frame_json=json.dumps(frame.model_dump(), indent=2),
            shallow_outputs_json=json.dumps(
                [s.model_dump() for s in shallow_outputs], indent=2
            ),
            salience_json=json.dumps(salience.model_dump(), indent=2),
            deep_outputs_json=json.dumps(
                [d.model_dump() for d in deep_outputs], indent=2
            ),
            cross_exam_json=json.dumps([c.model_dump() for c in cross_exam], indent=2),
            collisions_json=json.dumps(
                [c.model_dump() for c in (collisions or [])], indent=2
            ),
        )

        try:
            from protocols.config import SYNTHESIS_THINKING_BUDGET

            synth_budget = max(self.thinking_budget, SYNTHESIS_THINKING_BUDGET)
            synth_engine = SynthesisEngine(
                self.client,
                self.thinking_model,
                synth_budget,
                use_agent=True,
            )
            raw = await synth_engine.synthesize(
                protocol_prompt=prompt, question=question
            )

            # Split JSON and prose
            synthesis = None
            prose = raw
            if "---PROSE---" in raw:
                json_part, prose = raw.split("---PROSE---", 1)
                try:
                    data = parse_json_object(json_part)
                    synthesis = WalkSynthesis.model_validate(data)
                except Exception:
                    _log.warning("Failed to parse synthesis JSON, using raw text")
            else:
                try:
                    data = parse_json_object(raw)
                    synthesis = WalkSynthesis.model_validate(data)
                except Exception:
                    pass

            end_span(span, output=f"synthesis {len(prose)} chars")
            return synthesis, prose.strip()
        except Exception:
            end_span(span, error="synthesis failed")
            raise

    async def _stage_provocation(
        self,
        frame: FrameArtifact,
        shallow_outputs: list[ShallowWalkOutput],
        deep_outputs: list[DeepWalkOutput],
        collisions: list[CollisionFusion],
    ) -> WalkProvocation | None:
        """Stage 6: Provocation — walk-back-to-desk bridge (L4).

        Produces 3 sharpest verbatim statements (often from periphery lenses),
        their contradictions, the most underdeveloped thread, and a follow-up
        prompt to sit with at the desk. NOT a summary. NOT a decision aid.
        Returns None on parse failure — never fails the run.
        """
        print("Stage 6: Generating provocation...")
        span = create_span("stage:provocation", {})

        prompt = PROVOCATION_PROMPT.format(
            frame_json=json.dumps(frame.model_dump(), indent=2),
            shallow_outputs_json=json.dumps(
                [s.model_dump() for s in shallow_outputs], indent=2
            ),
            deep_outputs_json=json.dumps(
                [d.model_dump() for d in deep_outputs], indent=2
            ),
            collisions_json=json.dumps([c.model_dump() for c in collisions], indent=2),
        )

        try:
            assert self._synthesizer is not None
            raw = await agent_complete(
                agent=self._synthesizer,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )
            data = parse_json_object(raw)
            provocation = WalkProvocation.model_validate(data)
            end_span(
                span,
                output=f"provocation: {len(provocation.sharpest_statements)} statements",
            )
            return provocation
        except Exception as e:
            _log.warning("Provocation stage failed: %s", e)
            end_span(span, error="provocation failed (non-fatal)")
            return None
