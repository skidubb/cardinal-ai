"""P24 Causal Loop Mapping — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    VARIABLE_EXTRACTION_PROMPT,
    DEDUPLICATION_PROMPT,
    CAUSAL_LINK_PROMPT,
    LEVERAGE_POINT_PROMPT,
)

P24_DEF = ProtocolDef(
    protocol_id="p24_causal_loop_mapping",
    stages=[
        Stage(
            name="extract_variables",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_variables",
                prompt_template=VARIABLE_EXTRACTION_PROMPT,
            ),
        ),
        Stage(
            name="deduplicate",
            trigger=after("raw_variables"),
            execute=mechanical_stage(
                topic_in="raw_variables",
                topic_out="deduped_variables",
                prompt_template=DEDUPLICATION_PROMPT,
            ),
        ),
        Stage(
            name="causal_links",
            trigger=after("deduped_variables"),
            execute=parallel_agent_stage(
                topic_in="deduped_variables",
                topic_out="causal_links",
                prompt_template=CAUSAL_LINK_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("causal_links"),
            execute=synthesis_stage(
                topics_in=["causal_links"],
                topic_out="synthesis",
                prompt_template=LEVERAGE_POINT_PROMPT,
            ),
        ),
    ],
)
