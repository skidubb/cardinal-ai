"""P41 Duke Decision Quality Separation — blackboard protocol definition.

2 stages: process_evaluation → assessment.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage
from .prompts import (
    PROCESS_EVALUATION_PROMPT,
    ASSESSMENT_PROMPT,
)


P41_DEF = ProtocolDef(
    protocol_id="p41_duke_decision_quality",
    stages=[
        Stage(
            name="process_evaluation",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="scores",
                prompt_template=PROCESS_EVALUATION_PROMPT,
            ),
        ),
        Stage(
            name="assessment",
            trigger=after("scores"),
            execute=mechanical_stage(
                topic_in="scores",
                topic_out="synthesis",
                prompt_template=ASSESSMENT_PROMPT,
            ),
        ),
    ],
)
