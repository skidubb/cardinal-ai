"""P0b Skip Gate — blackboard protocol definition.

2 mechanical stages: feature_extraction → gate_decision.
If skip → a single agent response stage fires.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage, sequential_agent_stage
from .prompts import (
    FEATURE_EXTRACTION_PROMPT,
    GATE_DECISION_PROMPT,
    SINGLE_AGENT_PROMPT,
)


P0B_DEF = ProtocolDef(
    protocol_id="p0b_skip_gate",
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
            name="gate_decision",
            trigger=after("features"),
            execute=mechanical_stage(
                topic_in="features",
                topic_out="gate",
                prompt_template=GATE_DECISION_PROMPT,
            ),
        ),
        Stage(
            name="single_agent_response",
            trigger=after("gate"),
            execute=sequential_agent_stage(
                topic_in="question",
                topic_out="response",
                prompt_template=SINGLE_AGENT_PROMPT,
            ),
        ),
    ],
)
