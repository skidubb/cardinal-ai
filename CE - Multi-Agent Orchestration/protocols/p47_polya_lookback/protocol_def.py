"""P47 Polya Look-Back — blackboard protocol definition.

Sequential 3 stages: method_analysis → generalization → meta_synthesis.
All mechanical (reflection on prior protocol output, no agents needed).
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage
from .prompts import (
    METHOD_ANALYSIS_PROMPT,
    GENERALIZATION_PROMPT,
    META_SYNTHESIS_PROMPT,
)


P47_DEF = ProtocolDef(
    protocol_id="p47_polya_lookback",
    stages=[
        Stage(
            name="method_analysis",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="method_analysis",
                prompt_template=METHOD_ANALYSIS_PROMPT,
            ),
        ),
        Stage(
            name="generalization",
            trigger=after("method_analysis"),
            execute=mechanical_stage(
                topic_in="method_analysis",
                topic_out="generalization",
                prompt_template=GENERALIZATION_PROMPT,
            ),
        ),
        Stage(
            name="meta_synthesis",
            trigger=after("generalization"),
            execute=mechanical_stage(
                topic_in="generalization",
                topic_out="routing_rule",
                prompt_template=META_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
