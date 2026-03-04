"""P16 Analysis of Competing Hypotheses — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    HYPOTHESIS_GENERATION_PROMPT,
    EVIDENCE_LISTING_PROMPT,
    MATRIX_SCORING_PROMPT,
    SENSITIVITY_SYNTHESIS_PROMPT,
)

P16_DEF = ProtocolDef(
    protocol_id="p16_ach",
    stages=[
        Stage(
            name="generate_hypotheses",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="hypotheses",
                prompt_template=HYPOTHESIS_GENERATION_PROMPT,
            ),
        ),
        Stage(
            name="list_evidence",
            trigger=after("hypotheses"),
            execute=mechanical_stage(
                topic_in="hypotheses",
                topic_out="evidence",
                prompt_template=EVIDENCE_LISTING_PROMPT,
            ),
        ),
        Stage(
            name="score_matrix",
            trigger=after("evidence"),
            execute=parallel_agent_stage(
                topic_in="evidence",
                topic_out="scores",
                prompt_template=MATRIX_SCORING_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("scores"),
            execute=synthesis_stage(
                topics_in=["scores"],
                topic_out="synthesis",
                prompt_template=SENSITIVITY_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
