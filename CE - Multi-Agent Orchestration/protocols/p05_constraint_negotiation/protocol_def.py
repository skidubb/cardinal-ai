"""P05 Constraint Negotiation — blackboard protocol definition.

3 stages: opening → negotiation_rounds (multi-round) → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, multi_round_stage, synthesis_stage
from .prompts import (
    OPENING_PROMPT,
    REVISION_PROMPT,
    SYNTHESIS_PROMPT,
)


P05_DEF = ProtocolDef(
    protocol_id="p05_constraint_negotiation",
    stages=[
        Stage(
            name="opening",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="negotiation_round_0",
                prompt_template=OPENING_PROMPT,
            ),
        ),
        Stage(
            name="negotiation_rounds",
            trigger=after("negotiation_round_0"),
            execute=multi_round_stage(
                topic_base="negotiation",
                prompt_template=REVISION_PROMPT,
                max_rounds=3,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("negotiation_complete"),
            execute=synthesis_stage(
                topics_in=[
                    "negotiation_round_0",
                    "negotiation_round_1",
                    "negotiation_round_2",
                    "negotiation_round_3",
                ],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
