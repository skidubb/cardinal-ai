"""P45 Whitehead Process-Entity Weights — blackboard protocol definition.

Data-driven: single mechanical synthesis stage over rankings input.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always
from protocols.stages import mechanical_stage
from .prompts import RECOMMEND_SYNTHESIS_PROMPT


P45_DEF = ProtocolDef(
    protocol_id="p45_whitehead_weights",
    stages=[
        Stage(
            name="synthesize_rankings",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="synthesis",
                prompt_template=RECOMMEND_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
