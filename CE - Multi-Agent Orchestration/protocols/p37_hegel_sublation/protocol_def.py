"""P37 Hegel Sublation Synthesis — blackboard protocol definition.

3 stages: thesis → antithesis → sublation.
Sequential dialectic: thesis advocates, antithesis advocates, then synthesis transcends both.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, synthesis_stage
from .prompts import (
    THESIS_PROMPT,
    ANTITHESIS_PROMPT,
    SUBLATION_PROMPT,
)


P37_DEF = ProtocolDef(
    protocol_id="p37_hegel_sublation",
    stages=[
        Stage(
            name="thesis",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="thesis",
                prompt_template=THESIS_PROMPT,
            ),
        ),
        Stage(
            name="antithesis",
            trigger=after("thesis"),
            execute=parallel_agent_stage(
                topic_in="thesis",
                topic_out="antithesis",
                prompt_template=ANTITHESIS_PROMPT,
            ),
        ),
        Stage(
            name="sublation",
            trigger=after("antithesis"),
            execute=synthesis_stage(
                topics_in=["thesis", "antithesis"],
                topic_out="synthesis",
                prompt_template=SUBLATION_PROMPT,
            ),
        ),
    ],
)
