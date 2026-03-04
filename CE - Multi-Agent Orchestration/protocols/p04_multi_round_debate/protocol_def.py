"""P04 Multi-Round Debate — blackboard protocol definition.

3 stages: opening → debate_rounds (multi-round) → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, multi_round_stage, synthesis_stage
from .prompts import (
    OPENING_PROMPT,
    REBUTTAL_PROMPT,
    SYNTHESIS_PROMPT,
)


P04_DEF = ProtocolDef(
    protocol_id="p04_multi_round_debate",
    stages=[
        Stage(
            name="opening",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="debate_round_0",
                prompt_template=OPENING_PROMPT,
            ),
        ),
        Stage(
            name="debate_rounds",
            trigger=after("debate_round_0"),
            execute=multi_round_stage(
                topic_base="debate",
                prompt_template=REBUTTAL_PROMPT,
                max_rounds=3,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("debate_complete"),
            execute=synthesis_stage(
                topics_in=[
                    "debate_round_0",
                    "debate_round_1",
                    "debate_round_2",
                    "debate_round_3",
                ],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
