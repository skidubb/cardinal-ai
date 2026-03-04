"""P28 Six Thinking Hats — blackboard protocol definition.

6 stages: blue_framing → white_hat → red_hat → black_hat → yellow_hat → green_hat → synthesis.
Each hat runs all agents in parallel; hats run sequentially.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    BLUE_HAT_FRAMING_PROMPT,
    WHITE_HAT_PROMPT,
    RED_HAT_PROMPT,
    BLACK_HAT_PROMPT,
    YELLOW_HAT_PROMPT,
    GREEN_HAT_PROMPT,
    BLUE_HAT_SYNTHESIS_PROMPT,
)


P28_DEF = ProtocolDef(
    protocol_id="p28_six_hats",
    stages=[
        Stage(
            name="blue_framing",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="framing",
                prompt_template=BLUE_HAT_FRAMING_PROMPT,
            ),
        ),
        Stage(
            name="white_hat",
            trigger=after("framing"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="white_hat_outputs",
                prompt_template=WHITE_HAT_PROMPT,
            ),
        ),
        Stage(
            name="red_hat",
            trigger=after("white_hat_outputs"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="red_hat_outputs",
                prompt_template=RED_HAT_PROMPT,
            ),
        ),
        Stage(
            name="black_hat",
            trigger=after("red_hat_outputs"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="black_hat_outputs",
                prompt_template=BLACK_HAT_PROMPT,
            ),
        ),
        Stage(
            name="yellow_hat",
            trigger=after("black_hat_outputs"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="yellow_hat_outputs",
                prompt_template=YELLOW_HAT_PROMPT,
            ),
        ),
        Stage(
            name="green_hat",
            trigger=after("yellow_hat_outputs"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="green_hat_outputs",
                prompt_template=GREEN_HAT_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("green_hat_outputs"),
            execute=synthesis_stage(
                topics_in=[
                    "white_hat_outputs",
                    "red_hat_outputs",
                    "black_hat_outputs",
                    "yellow_hat_outputs",
                    "green_hat_outputs",
                ],
                topic_out="synthesis",
                prompt_template=BLUE_HAT_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
