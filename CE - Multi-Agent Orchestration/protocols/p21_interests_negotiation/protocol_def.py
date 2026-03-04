"""P21 Interests-Based Negotiation — blackboard protocol definition.

5 stages: surface_interests → interest_map → generate_options → score_options → final_agreement.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import (
    parallel_agent_stage,
    mechanical_stage,
    synthesis_stage,
)
from .prompts import (
    SURFACE_INTERESTS_PROMPT,
    INTEREST_MAP_PROMPT,
    GENERATE_OPTIONS_PROMPT,
    SCORE_OPTIONS_PROMPT,
    FINAL_AGREEMENT_PROMPT,
)


P21_DEF = ProtocolDef(
    protocol_id="p21_interests_negotiation",
    stages=[
        Stage(
            name="surface_interests",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="interests",
                prompt_template=SURFACE_INTERESTS_PROMPT,
            ),
        ),
        Stage(
            name="interest_map",
            trigger=after("interests"),
            execute=mechanical_stage(
                topic_in="interests",
                topic_out="interest_map",
                prompt_template=INTEREST_MAP_PROMPT,
            ),
        ),
        Stage(
            name="generate_options",
            trigger=after("interest_map"),
            execute=parallel_agent_stage(
                topic_in="interest_map",
                topic_out="options",
                prompt_template=GENERATE_OPTIONS_PROMPT,
            ),
        ),
        Stage(
            name="score_options",
            trigger=after("options"),
            execute=mechanical_stage(
                topic_in="options",
                topic_out="scored_options",
                prompt_template=SCORE_OPTIONS_PROMPT,
            ),
        ),
        Stage(
            name="final_agreement",
            trigger=after("scored_options"),
            execute=synthesis_stage(
                topics_in=["interest_map", "options", "scored_options"],
                topic_out="synthesis",
                prompt_template=FINAL_AGREEMENT_PROMPT,
            ),
        ),
    ],
)
