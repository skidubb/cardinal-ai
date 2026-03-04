"""P31 Wittgenstein Language Game — blackboard protocol definition.

4 stages: vocabulary_assignment → reframe → rank → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage, parallel_agent_stage, synthesis_stage
from .prompts import (
    VOCABULARY_ASSIGNMENT_PROMPT,
    REFRAME_PROMPT,
    RANKING_PROMPT,
    SYNTHESIS_PROMPT,
)


P31_DEF = ProtocolDef(
    protocol_id="p31_wittgenstein_language_game",
    stages=[
        Stage(
            name="vocabulary_assignment",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="assignments",
                prompt_template=VOCABULARY_ASSIGNMENT_PROMPT,
            ),
        ),
        Stage(
            name="reframe",
            trigger=after("assignments"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="reframings",
                prompt_template=REFRAME_PROMPT,
            ),
        ),
        Stage(
            name="rank",
            trigger=after("reframings"),
            execute=mechanical_stage(
                topic_in="reframings",
                topic_out="ranking",
                prompt_template=RANKING_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("ranking"),
            execute=synthesis_stage(
                topics_in=["assignments", "reframings", "ranking"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
