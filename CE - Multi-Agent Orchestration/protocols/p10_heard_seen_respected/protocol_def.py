"""P10 Heard Seen Respected — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    STAKEHOLDER_NARRATIVE_PROMPT,
    REFLECT_BACK_PROMPT,
    BRIDGE_SYNTHESIS_PROMPT,
)

P10_DEF = ProtocolDef(
    protocol_id="p10_heard_seen_respected",
    stages=[
        Stage(
            name="generate",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="narratives",
                prompt_template=STAKEHOLDER_NARRATIVE_PROMPT,
            ),
        ),
        Stage(
            name="reflect_back",
            trigger=after("narratives"),
            execute=mechanical_stage(
                topic_in="narratives",
                topic_out="reflections",
                prompt_template=REFLECT_BACK_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("reflections"),
            execute=synthesis_stage(
                topics_in=["reflections"],
                topic_out="synthesis",
                prompt_template=BRIDGE_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
