"""P07 Wicked Questions — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    TENSION_GENERATION_PROMPT,
    WICKEDNESS_TEST_PROMPT,
    RANKING_PROMPT,
    SYNTHESIS_PROMPT,
)

P07_DEF = ProtocolDef(
    protocol_id="p07_wicked_questions",
    stages=[
        Stage(
            name="generate",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_tensions",
                prompt_template=TENSION_GENERATION_PROMPT,
            ),
        ),
        Stage(
            name="wickedness_test",
            trigger=after("raw_tensions"),
            execute=mechanical_stage(
                topic_in="raw_tensions",
                topic_out="wicked_tested",
                prompt_template=WICKEDNESS_TEST_PROMPT,
            ),
        ),
        Stage(
            name="rank",
            trigger=after("wicked_tested"),
            execute=mechanical_stage(
                topic_in="wicked_tested",
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
