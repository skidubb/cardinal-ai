"""P03 Parallel Synthesis — blackboard protocol definition.

2 stages: parallel_query → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, synthesis_stage
from .prompts import SYNTHESIS_SYSTEM_PROMPT


P03_DEF = ProtocolDef(
    protocol_id="p03_parallel_synthesis",
    stages=[
        Stage(
            name="parallel_query",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="perspectives",
                prompt_template="{input}",
                use_thinking=True,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("perspectives"),
            execute=synthesis_stage(
                topics_in=["perspectives"],
                topic_out="synthesis",
                prompt_template=(
                    f"{SYNTHESIS_SYSTEM_PROMPT}\n\n"
                    "ORIGINAL QUESTION:\n{question}\n\n"
                    "INDEPENDENT PERSPECTIVES:\n{perspectives}"
                ),
            ),
        ),
    ],
)
