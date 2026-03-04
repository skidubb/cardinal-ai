"""P11 Discovery & Action Dialogue — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    SCOUT_DEVIANTS_PROMPT,
    FILTER_BEHAVIOR_PROMPT,
    EXTRACT_PRACTICES_PROMPT,
    ADAPT_RECOMMENDATIONS_PROMPT,
)

P11_DEF = ProtocolDef(
    protocol_id="p11_discovery_action_dialogue",
    stages=[
        Stage(
            name="scout_deviants",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_deviants",
                prompt_template=SCOUT_DEVIANTS_PROMPT,
            ),
        ),
        Stage(
            name="filter_behaviors",
            trigger=after("raw_deviants"),
            execute=mechanical_stage(
                topic_in="raw_deviants",
                topic_out="filtered_behaviors",
                prompt_template=FILTER_BEHAVIOR_PROMPT,
            ),
        ),
        Stage(
            name="extract_practices",
            trigger=after("filtered_behaviors"),
            execute=parallel_agent_stage(
                topic_in="filtered_behaviors",
                topic_out="practices",
                prompt_template=EXTRACT_PRACTICES_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("practices"),
            execute=synthesis_stage(
                topics_in=["practices"],
                topic_out="synthesis",
                prompt_template=ADAPT_RECOMMENDATIONS_PROMPT,
            ),
        ),
    ],
)
