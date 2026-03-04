"""P25 System Archetype Detection — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    DYNAMICS_OBSERVATION_PROMPT,
    DYNAMICS_MERGE_PROMPT,
    ARCHETYPE_MATCHING_PROMPT,
    SYNTHESIS_PROMPT,
)

P25_DEF = ProtocolDef(
    protocol_id="p25_system_archetype_detection",
    stages=[
        Stage(
            name="observe_dynamics",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="raw_dynamics",
                prompt_template=DYNAMICS_OBSERVATION_PROMPT,
            ),
        ),
        Stage(
            name="merge_dynamics",
            trigger=after("raw_dynamics"),
            execute=mechanical_stage(
                topic_in="raw_dynamics",
                topic_out="merged_dynamics",
                prompt_template=DYNAMICS_MERGE_PROMPT,
            ),
        ),
        Stage(
            name="match_archetypes",
            trigger=after("merged_dynamics"),
            execute=parallel_agent_stage(
                topic_in="merged_dynamics",
                topic_out="archetype_matches",
                prompt_template=ARCHETYPE_MATCHING_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("archetype_matches"),
            execute=synthesis_stage(
                topics_in=["archetype_matches"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
