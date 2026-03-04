"""P0a Reasoning Router — blackboard protocol definition.

3 mechanical stages: feature_extraction → problem_type → routing_decision.
No agents needed — all classification via orchestration model.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage
from .prompts import (
    FEATURE_EXTRACTION_PROMPT,
    PROBLEM_TYPE_PROMPT,
    ROUTING_DECISION_PROMPT,
)


P0A_DEF = ProtocolDef(
    protocol_id="p0a_reasoning_router",
    stages=[
        Stage(
            name="feature_extraction",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="features",
                prompt_template=FEATURE_EXTRACTION_PROMPT,
            ),
        ),
        Stage(
            name="problem_type",
            trigger=after("features"),
            execute=mechanical_stage(
                topic_in="features",
                topic_out="problem_type",
                prompt_template=PROBLEM_TYPE_PROMPT,
            ),
        ),
        Stage(
            name="routing_decision",
            trigger=after("problem_type"),
            execute=mechanical_stage(
                topic_in="problem_type",
                topic_out="routing",
                prompt_template=ROUTING_DECISION_PROMPT,
            ),
        ),
    ],
)
