"""P14 One-Two-Four-All — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    SOLO_IDEATION_PROMPT,
    PAIR_MERGE_PROMPT,
    QUAD_MERGE_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)

P14_DEF = ProtocolDef(
    protocol_id="p14_one_two_four_all",
    stages=[
        Stage(
            name="solo_ideation",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="solo_ideas",
                prompt_template=SOLO_IDEATION_PROMPT,
            ),
        ),
        Stage(
            name="pair_merge",
            trigger=after("solo_ideas"),
            execute=mechanical_stage(
                topic_in="solo_ideas",
                topic_out="pair_merged",
                prompt_template=PAIR_MERGE_PROMPT,
            ),
        ),
        Stage(
            name="quad_merge",
            trigger=after("pair_merged"),
            execute=mechanical_stage(
                topic_in="pair_merged",
                topic_out="quad_merged",
                prompt_template=QUAD_MERGE_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("quad_merged"),
            execute=synthesis_stage(
                topics_in=["quad_merged"],
                topic_out="synthesis",
                prompt_template=FINAL_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
