"""P36 Peirce Abduction Cycle — blackboard protocol definition.

4 stages: abduction → deduction → induction → loop_decision, then synthesis.
Uses multi_round_stage for the iterative abduction-deduction-induction cycle.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import (
    parallel_agent_stage,
    mechanical_stage,
    synthesis_stage,
)
from .prompts import (
    ABDUCTION_PROMPT,
    DEDUCTION_PROMPT,
    INDUCTION_PROMPT,
    LOOP_DECISION_PROMPT,
    SYNTHESIS_PROMPT,
)


def _abduction_converged(bb, round_num):
    """Stop if the loop decision says ACCEPT."""
    entries = bb.read(f"abduction_round_{round_num - 1}")
    return any("ACCEPT" in str(e.content) for e in entries)


P36_DEF = ProtocolDef(
    protocol_id="p36_peirce_abduction",
    stages=[
        Stage(
            name="abduction",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="hypotheses",
                prompt_template=ABDUCTION_PROMPT,
            ),
        ),
        Stage(
            name="deduction",
            trigger=after("hypotheses"),
            execute=parallel_agent_stage(
                topic_in="hypotheses",
                topic_out="predictions",
                prompt_template=DEDUCTION_PROMPT,
            ),
        ),
        Stage(
            name="induction",
            trigger=after("predictions"),
            execute=parallel_agent_stage(
                topic_in="predictions",
                topic_out="evidence_assessment",
                prompt_template=INDUCTION_PROMPT,
            ),
        ),
        Stage(
            name="loop_decision",
            trigger=after("evidence_assessment"),
            execute=mechanical_stage(
                topic_in="evidence_assessment",
                topic_out="cycle_history",
                prompt_template=LOOP_DECISION_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("cycle_history"),
            execute=synthesis_stage(
                topics_in=["hypotheses", "predictions", "evidence_assessment", "cycle_history"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
