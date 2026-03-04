"""P12 25/10 Crowd Sourcing — blackboard protocol definition.

3 stages: idea_generation → scoring_rounds (multi-round) → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, multi_round_stage, synthesis_stage
from .prompts import (
    IDEA_GENERATION_PROMPT,
    SCORING_PROMPT,
    SYNTHESIS_PROMPT,
)


P12_DEF = ProtocolDef(
    protocol_id="p12_twenty_five_ten",
    stages=[
        Stage(
            name="idea_generation",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="ideas",
                prompt_template=IDEA_GENERATION_PROMPT,
            ),
        ),
        Stage(
            name="scoring_rounds",
            trigger=after("ideas"),
            execute=multi_round_stage(
                topic_base="scoring",
                prompt_template=SCORING_PROMPT,
                max_rounds=3,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("scoring_complete"),
            execute=synthesis_stage(
                topics_in=["ideas", "scoring_round_1", "scoring_round_2", "scoring_round_3"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
