"""P32 Tetlock Calibrated Forecast — blackboard protocol definition.

5 stages: fermi_decomposition → base_rates → adjustments → extremizing → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    FERMI_DECOMPOSITION_PROMPT,
    BASE_RATE_PROMPT,
    INSIDE_VIEW_ADJUSTMENT_PROMPT,
    EXTREMIZING_AGGREGATION_PROMPT,
    SYNTHESIS_PROMPT,
)


P32_DEF = ProtocolDef(
    protocol_id="p32_tetlock_forecast",
    stages=[
        Stage(
            name="fermi_decomposition",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="decomposition",
                prompt_template=FERMI_DECOMPOSITION_PROMPT,
            ),
        ),
        Stage(
            name="base_rates",
            trigger=after("decomposition"),
            execute=parallel_agent_stage(
                topic_in="decomposition",
                topic_out="base_rates",
                prompt_template=BASE_RATE_PROMPT,
            ),
        ),
        Stage(
            name="adjustments",
            trigger=after("base_rates"),
            execute=parallel_agent_stage(
                topic_in="base_rates",
                topic_out="adjustments",
                prompt_template=INSIDE_VIEW_ADJUSTMENT_PROMPT,
            ),
        ),
        Stage(
            name="extremizing",
            trigger=after("adjustments"),
            execute=mechanical_stage(
                topic_in="adjustments",
                topic_out="final_probability",
                prompt_template=EXTREMIZING_AGGREGATION_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("final_probability"),
            execute=synthesis_stage(
                topics_in=["decomposition", "base_rates", "adjustments", "final_probability"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
