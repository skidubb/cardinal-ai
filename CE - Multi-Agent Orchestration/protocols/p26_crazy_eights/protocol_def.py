"""P26 Crazy Eights — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    RAPID_GENERATION_PROMPT,
    CLUSTER_PROMPT,
    DOT_VOTE_PROMPT,
    DEVELOP_CONCEPTS_PROMPT,
)

P26_DEF = ProtocolDef(
    protocol_id="p26_crazy_eights",
    stages=[
        Stage(
            name="rapid_generate",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_ideas",
                prompt_template=RAPID_GENERATION_PROMPT,
            ),
        ),
        Stage(
            name="cluster",
            trigger=after("raw_ideas"),
            execute=mechanical_stage(
                topic_in="raw_ideas",
                topic_out="clustered",
                prompt_template=CLUSTER_PROMPT,
            ),
        ),
        Stage(
            name="dot_vote",
            trigger=after("clustered"),
            execute=mechanical_stage(
                topic_in="clustered",
                topic_out="voted",
                prompt_template=DOT_VOTE_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("voted"),
            execute=synthesis_stage(
                topics_in=["voted"],
                topic_out="synthesis",
                prompt_template=DEVELOP_CONCEPTS_PROMPT,
            ),
        ),
    ],
)
