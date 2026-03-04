"""P08 Min Specs — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    GENERATE_SPECS_PROMPT,
    DEDUP_SPECS_PROMPT,
    ELIMINATION_TEST_PROMPT,
    BORDERLINE_VOTE_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)

P08_DEF = ProtocolDef(
    protocol_id="p08_min_specs",
    stages=[
        Stage(
            name="generate",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_specs",
                prompt_template=GENERATE_SPECS_PROMPT,
            ),
        ),
        Stage(
            name="deduplicate",
            trigger=after("raw_specs"),
            execute=mechanical_stage(
                topic_in="raw_specs",
                topic_out="deduped_specs",
                prompt_template=DEDUP_SPECS_PROMPT,
            ),
        ),
        Stage(
            name="elimination_test",
            trigger=after("deduped_specs"),
            execute=mechanical_stage(
                topic_in="deduped_specs",
                topic_out="tested_specs",
                prompt_template=ELIMINATION_TEST_PROMPT,
            ),
        ),
        Stage(
            name="borderline_vote",
            trigger=after("tested_specs"),
            execute=mechanical_stage(
                topic_in="tested_specs",
                topic_out="voted_specs",
                prompt_template=BORDERLINE_VOTE_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("voted_specs"),
            execute=synthesis_stage(
                topics_in=["voted_specs"],
                topic_out="synthesis",
                prompt_template=FINAL_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
