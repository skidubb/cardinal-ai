"""P18 Delphi Method — blackboard protocol definition.

3 stages: initial_estimates → revision_rounds (multi-round) → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, multi_round_stage, synthesis_stage
from .prompts import (
    INITIAL_ESTIMATE_PROMPT,
    REVISION_ESTIMATE_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)


P18_DEF = ProtocolDef(
    protocol_id="p18_delphi_method",
    stages=[
        Stage(
            name="initial_estimates",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="estimates_round_0",
                prompt_template=INITIAL_ESTIMATE_PROMPT,
            ),
        ),
        Stage(
            name="revision_rounds",
            trigger=after("estimates_round_0"),
            execute=multi_round_stage(
                topic_base="estimates",
                prompt_template=REVISION_ESTIMATE_PROMPT,
                max_rounds=3,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("estimates_complete"),
            execute=synthesis_stage(
                topics_in=[
                    "estimates_round_0",
                    "estimates_round_1",
                    "estimates_round_2",
                    "estimates_round_3",
                ],
                topic_out="synthesis",
                prompt_template=FINAL_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
