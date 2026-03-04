"""P39 Popper Falsification Gate — blackboard protocol definition.

3 stages: generate_conditions → evidence_search → verdict.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, synthesis_stage
from .prompts import (
    GENERATE_CONDITIONS_PROMPT,
    EVIDENCE_SEARCH_PROMPT,
    VERDICT_PROMPT,
)


P39_DEF = ProtocolDef(
    protocol_id="p39_popper_falsification",
    stages=[
        Stage(
            name="generate_conditions",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="conditions",
                prompt_template=GENERATE_CONDITIONS_PROMPT,
            ),
        ),
        Stage(
            name="evidence_search",
            trigger=after("conditions"),
            execute=parallel_agent_stage(
                topic_in="conditions",
                topic_out="conditions_evidence",
                prompt_template=EVIDENCE_SEARCH_PROMPT,
            ),
        ),
        Stage(
            name="verdict",
            trigger=after("conditions_evidence"),
            execute=synthesis_stage(
                topics_in=["conditions_evidence"],
                topic_out="synthesis",
                prompt_template=VERDICT_PROMPT,
            ),
        ),
    ],
)
