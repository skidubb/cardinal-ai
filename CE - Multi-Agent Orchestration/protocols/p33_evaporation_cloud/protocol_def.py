"""P33 Goldratt Evaporation Cloud — blackboard protocol definition.

4 stages: map_cloud → surface_assumptions → conflict_assumptions → injection_synthesis.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage, parallel_agent_stage, synthesis_stage
from .prompts import (
    MAP_CLOUD_PROMPT,
    ASSUMPTION_PROMPT,
    CONFLICT_ASSUMPTION_PROMPT,
    INJECTION_PROMPT,
)


P33_DEF = ProtocolDef(
    protocol_id="p33_evaporation_cloud",
    stages=[
        Stage(
            name="map_cloud",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="cloud",
                prompt_template=MAP_CLOUD_PROMPT,
            ),
        ),
        Stage(
            name="surface_assumptions",
            trigger=after("cloud"),
            execute=parallel_agent_stage(
                topic_in="cloud",
                topic_out="assumptions",
                prompt_template=ASSUMPTION_PROMPT,
            ),
        ),
        Stage(
            name="conflict_assumptions",
            trigger=after("assumptions"),
            execute=parallel_agent_stage(
                topic_in="cloud",
                topic_out="conflict_assumptions",
                prompt_template=CONFLICT_ASSUMPTION_PROMPT,
            ),
        ),
        Stage(
            name="injection_synthesis",
            trigger=after("conflict_assumptions"),
            execute=synthesis_stage(
                topics_in=["cloud", "assumptions", "conflict_assumptions"],
                topic_out="synthesis",
                prompt_template=INJECTION_PROMPT,
            ),
        ),
    ],
)
