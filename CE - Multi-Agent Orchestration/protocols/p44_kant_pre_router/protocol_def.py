"""P44 Kant Architectonic Pre-Router — blackboard protocol definition.

Single mechanical classification stage.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always
from protocols.stages import mechanical_stage
from .prompts import CLASSIFICATION_PROMPT


P44_DEF = ProtocolDef(
    protocol_id="p44_kant_pre_router",
    stages=[
        Stage(
            name="classify",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="classification",
                prompt_template=CLASSIFICATION_PROMPT,
            ),
        ),
    ],
)
