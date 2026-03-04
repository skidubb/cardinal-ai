"""P17 Red/Blue/White Team — blackboard protocol definition.

4 stages: red_attack → blue_defense (scoped) → white_adjudicate → final_assessment.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import (
    parallel_agent_stage,
    scoped_parallel_stage,
    mechanical_stage,
    synthesis_stage,
)
from .prompts import (
    RED_ATTACK_PROMPT,
    BLUE_DEFENSE_PROMPT,
    WHITE_ADJUDICATE_PROMPT,
    FINAL_ASSESSMENT_PROMPT,
)


P17_DEF = ProtocolDef(
    protocol_id="p17_red_blue_white",
    stages=[
        Stage(
            name="red_attack",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="attacks",
                prompt_template=RED_ATTACK_PROMPT,
            ),
        ),
        Stage(
            name="blue_defense",
            trigger=after("attacks"),
            execute=scoped_parallel_stage(
                topic_in="attacks",
                topic_out="defenses",
                prompt_template=BLUE_DEFENSE_PROMPT,
            ),
        ),
        Stage(
            name="white_adjudicate",
            trigger=after("defenses"),
            execute=mechanical_stage(
                topic_in="defenses",
                topic_out="adjudication",
                prompt_template=WHITE_ADJUDICATE_PROMPT,
            ),
        ),
        Stage(
            name="final_assessment",
            trigger=after("adjudication"),
            execute=synthesis_stage(
                topics_in=["attacks", "defenses", "adjudication"],
                topic_out="synthesis",
                prompt_template=FINAL_ASSESSMENT_PROMPT,
            ),
        ),
    ],
)
