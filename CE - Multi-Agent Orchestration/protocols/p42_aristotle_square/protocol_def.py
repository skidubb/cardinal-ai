"""P42 Aristotle Square of Opposition — blackboard protocol definition.

Single mechanical classification stage.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always
from protocols.stages import mechanical_stage
from .prompts import CLASSIFICATION_PROMPT


P42_DEF = ProtocolDef(
    protocol_id="p42_aristotle_square",
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
