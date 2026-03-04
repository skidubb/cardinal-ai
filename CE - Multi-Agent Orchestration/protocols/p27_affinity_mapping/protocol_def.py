"""P27 Affinity Mapping — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    GENERATE_ITEMS_PROMPT,
    CLUSTER_ITEMS_PROMPT,
    LABEL_VALIDATE_PROMPT,
    HIERARCHY_SYNTHESIS_PROMPT,
)

P27_DEF = ProtocolDef(
    protocol_id="p27_affinity_mapping",
    stages=[
        Stage(
            name="generate_items",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_items",
                prompt_template=GENERATE_ITEMS_PROMPT,
            ),
        ),
        Stage(
            name="cluster_items",
            trigger=after("raw_items"),
            execute=mechanical_stage(
                topic_in="raw_items",
                topic_out="clustered",
                prompt_template=CLUSTER_ITEMS_PROMPT,
            ),
        ),
        Stage(
            name="label_validate",
            trigger=after("clustered"),
            execute=mechanical_stage(
                topic_in="clustered",
                topic_out="labeled",
                prompt_template=LABEL_VALIDATE_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("labeled"),
            execute=synthesis_stage(
                topics_in=["labeled"],
                topic_out="synthesis",
                prompt_template=HIERARCHY_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
