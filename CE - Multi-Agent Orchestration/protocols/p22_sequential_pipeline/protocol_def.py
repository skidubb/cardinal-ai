"""P22 Sequential Pipeline — blackboard protocol definition.

3 stages: sequential_processing → quality_gate → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import sequential_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    STAGE_PROMPT,
    QUALITY_GATE_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)


P22_DEF = ProtocolDef(
    protocol_id="p22_sequential_pipeline",
    stages=[
        Stage(
            name="sequential_processing",
            trigger=always(),
            execute=sequential_agent_stage(
                topic_in="question",
                topic_out="stage_outputs",
                prompt_template=STAGE_PROMPT,
            ),
        ),
        Stage(
            name="quality_gate",
            trigger=after("stage_outputs"),
            execute=mechanical_stage(
                topic_in="stage_outputs",
                topic_out="gate_result",
                prompt_template=QUALITY_GATE_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("gate_result"),
            execute=synthesis_stage(
                topics_in=["stage_outputs"],
                topic_out="synthesis",
                prompt_template=FINAL_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
