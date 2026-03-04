"""P40 Boyd OODA Rapid Cycle — blackboard protocol definition.

Uses multi_round_stage for iterative OODA cycles, then synthesis.
Each round covers observe→orient→decide→act as a single prompt cycle.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import (
    parallel_agent_stage,
    mechanical_stage,
    multi_round_stage,
    synthesis_stage,
)
from .prompts import (
    OBSERVE_PROMPT,
    ORIENT_PROMPT,
    DECIDE_PROMPT,
    ACT_PROMPT,
    SYNTHESIS_PROMPT,
)


P40_DEF = ProtocolDef(
    protocol_id="p40_boyd_ooda",
    stages=[
        Stage(
            name="observe",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="observations",
                prompt_template=OBSERVE_PROMPT,
            ),
        ),
        Stage(
            name="orient",
            trigger=after("observations"),
            execute=mechanical_stage(
                topic_in="observations",
                topic_out="model",
                prompt_template=ORIENT_PROMPT,
            ),
        ),
        Stage(
            name="decide",
            trigger=after("model"),
            execute=mechanical_stage(
                topic_in="model",
                topic_out="decision",
                prompt_template=DECIDE_PROMPT,
            ),
        ),
        Stage(
            name="act",
            trigger=after("decision"),
            execute=mechanical_stage(
                topic_in="decision",
                topic_out="cycles_json",
                prompt_template=ACT_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("cycles_json"),
            execute=synthesis_stage(
                topics_in=["observations", "model", "decision", "cycles_json"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
