"""P15 What / So What / Now What — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    WHAT_PROMPT,
    CONSOLIDATE_OBSERVATIONS_PROMPT,
    SO_WHAT_PROMPT,
    CONSOLIDATE_IMPLICATIONS_PROMPT,
    NOW_WHAT_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)

P15_DEF = ProtocolDef(
    protocol_id="p15_what_so_what_now_what",
    stages=[
        Stage(
            name="what",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="observations",
                prompt_template=WHAT_PROMPT,
            ),
        ),
        Stage(
            name="consolidate_observations",
            trigger=after("observations"),
            execute=mechanical_stage(
                topic_in="observations",
                topic_out="consolidated_observations",
                prompt_template=CONSOLIDATE_OBSERVATIONS_PROMPT,
            ),
        ),
        Stage(
            name="so_what",
            trigger=after("consolidated_observations"),
            execute=parallel_agent_stage(
                topic_in="consolidated_observations",
                topic_out="implications",
                prompt_template=SO_WHAT_PROMPT,
            ),
        ),
        Stage(
            name="consolidate_implications",
            trigger=after("implications"),
            execute=mechanical_stage(
                topic_in="implications",
                topic_out="consolidated_implications",
                prompt_template=CONSOLIDATE_IMPLICATIONS_PROMPT,
            ),
        ),
        Stage(
            name="now_what",
            trigger=after("consolidated_implications"),
            execute=parallel_agent_stage(
                topic_in="consolidated_implications",
                topic_out="actions",
                prompt_template=NOW_WHAT_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("actions"),
            execute=synthesis_stage(
                topics_in=["actions"],
                topic_out="synthesis",
                prompt_template=FINAL_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
