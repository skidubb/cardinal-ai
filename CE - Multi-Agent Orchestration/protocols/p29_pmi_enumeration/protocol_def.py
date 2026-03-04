"""P29 PMI Enumeration — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after, after_all
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    PROPOSITION_FRAMING_PROMPT,
    PLUS_PROMPT,
    MINUS_PROMPT,
    INTERESTING_PROMPT,
    SYNTHESIS_PROMPT,
)

P29_DEF = ProtocolDef(
    protocol_id="p29_pmi_enumeration",
    stages=[
        Stage(
            name="frame_proposition",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="proposition",
                prompt_template=PROPOSITION_FRAMING_PROMPT,
            ),
        ),
        Stage(
            name="plus",
            trigger=after("proposition"),
            execute=parallel_agent_stage(
                topic_in="proposition",
                topic_out="plus_points",
                prompt_template=PLUS_PROMPT,
            ),
        ),
        Stage(
            name="minus",
            trigger=after("proposition"),
            execute=parallel_agent_stage(
                topic_in="proposition",
                topic_out="minus_points",
                prompt_template=MINUS_PROMPT,
            ),
        ),
        Stage(
            name="interesting",
            trigger=after("proposition"),
            execute=parallel_agent_stage(
                topic_in="proposition",
                topic_out="interesting_points",
                prompt_template=INTERESTING_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after_all("plus_points", "minus_points", "interesting_points"),
            execute=synthesis_stage(
                topics_in=["plus_points", "minus_points", "interesting_points"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
