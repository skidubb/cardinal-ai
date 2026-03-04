"""P46 Incubation Protocol (The Walk) — blackboard protocol definition.

4 stages: analysis → compression → free_association → evaluation.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    ANALYSIS_PROMPT,
    COMPRESSION_PROMPT,
    FREE_ASSOCIATION_PROMPT,
    EVALUATION_PROMPT,
)


P46_DEF = ProtocolDef(
    protocol_id="p46_incubation",
    stages=[
        Stage(
            name="analysis",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="analyses",
                prompt_template=ANALYSIS_PROMPT,
            ),
        ),
        Stage(
            name="compression",
            trigger=after("analyses"),
            execute=mechanical_stage(
                topic_in="analyses",
                topic_out="tension",
                prompt_template=COMPRESSION_PROMPT,
            ),
        ),
        Stage(
            name="free_association",
            trigger=after("tension"),
            execute=parallel_agent_stage(
                topic_in="tension",
                topic_out="associations",
                prompt_template=FREE_ASSOCIATION_PROMPT,
            ),
        ),
        Stage(
            name="evaluation",
            trigger=after("associations"),
            execute=synthesis_stage(
                topics_in=["analyses", "tension", "associations"],
                topic_out="synthesis",
                prompt_template=EVALUATION_PROMPT,
            ),
        ),
    ],
)
