"""P13 Ecocycle Planning — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    ASSESS_INITIATIVES_PROMPT,
    RESOLVE_CONTESTED_PROMPT,
    ACTION_PLAN_PROMPT,
)

P13_DEF = ProtocolDef(
    protocol_id="p13_ecocycle_planning",
    stages=[
        Stage(
            name="assess",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="assessments",
                prompt_template=ASSESS_INITIATIVES_PROMPT,
            ),
        ),
        Stage(
            name="resolve_contested",
            trigger=after("assessments"),
            execute=mechanical_stage(
                topic_in="assessments",
                topic_out="resolved",
                prompt_template=RESOLVE_CONTESTED_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("resolved"),
            execute=synthesis_stage(
                topics_in=["resolved"],
                topic_out="synthesis",
                prompt_template=ACTION_PLAN_PROMPT,
            ),
        ),
    ],
)
