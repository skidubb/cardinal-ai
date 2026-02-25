"""P06 TRIZ Inversion — blackboard protocol definition.

5 stages: generate_failures → deduplicate → invert → rank → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    FAILURE_GENERATION_PROMPT,
    DEDUPLICATION_PROMPT,
    INVERSION_PROMPT,
    RANKING_PROMPT,
    SYNTHESIS_PROMPT,
)


P06_DEF = ProtocolDef(
    protocol_id="p06_triz",
    stages=[
        Stage(
            name="generate_failures",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_failures",
                prompt_template=FAILURE_GENERATION_PROMPT,
                use_thinking=True,
            ),
        ),
        Stage(
            name="deduplicate",
            trigger=after("raw_failures"),
            execute=mechanical_stage(
                topic_in="raw_failures",
                topic_out="failures",
                prompt_template=DEDUPLICATION_PROMPT,
            ),
        ),
        Stage(
            name="invert",
            trigger=after("failures"),
            execute=mechanical_stage(
                topic_in="failures",
                topic_out="solutions",
                prompt_template=INVERSION_PROMPT,
            ),
        ),
        Stage(
            name="rank",
            trigger=after("solutions"),
            execute=mechanical_stage(
                topic_in="solutions",
                topic_out="ranked",
                prompt_template=RANKING_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("ranked"),
            execute=synthesis_stage(
                topics_in=["ranked"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
