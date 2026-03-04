"""P38 Klein Pre-Mortem — blackboard protocol definition.

3 stages: failure_narratives → failure_extraction → mitigation_synthesis.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    FAILURE_NARRATIVE_PROMPT,
    FAILURE_EXTRACTION_PROMPT,
    MITIGATION_SYNTHESIS_PROMPT,
)


P38_DEF = ProtocolDef(
    protocol_id="p38_klein_premortem",
    stages=[
        Stage(
            name="failure_narratives",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="all_narratives",
                prompt_template=FAILURE_NARRATIVE_PROMPT,
            ),
        ),
        Stage(
            name="failure_extraction",
            trigger=after("all_narratives"),
            execute=mechanical_stage(
                topic_in="all_narratives",
                topic_out="failure_modes",
                prompt_template=FAILURE_EXTRACTION_PROMPT,
            ),
        ),
        Stage(
            name="mitigation_synthesis",
            trigger=after("failure_modes"),
            execute=synthesis_stage(
                topics_in=["failure_modes"],
                topic_out="synthesis",
                prompt_template=MITIGATION_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
