"""P30 Llull Combinatorial Association — blackboard protocol definition.

4 stages: define_disks → generate_combinations → evaluate_combinations → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage, parallel_agent_stage, synthesis_stage
from .prompts import (
    DEFINE_DISKS_PROMPT,
    GENERATE_COMBINATIONS_PROMPT,
    EVALUATE_COMBINATIONS_PROMPT,
    SYNTHESIS_PROMPT,
)


P30_DEF = ProtocolDef(
    protocol_id="p30_llull_combinatorial",
    stages=[
        Stage(
            name="define_disks",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="disks",
                prompt_template=DEFINE_DISKS_PROMPT,
            ),
        ),
        Stage(
            name="generate_combinations",
            trigger=after("disks"),
            execute=parallel_agent_stage(
                topic_in="disks",
                topic_out="combinations",
                prompt_template=GENERATE_COMBINATIONS_PROMPT,
            ),
        ),
        Stage(
            name="evaluate_combinations",
            trigger=after("combinations"),
            execute=parallel_agent_stage(
                topic_in="combinations",
                topic_out="evaluations",
                prompt_template=EVALUATE_COMBINATIONS_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("evaluations"),
            execute=synthesis_stage(
                topics_in=["disks", "evaluations"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
