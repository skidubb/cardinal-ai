"""Airport 5G Pipeline — blackboard protocol definition.

4-phase chained protocol: Discover → Diagnose → Negotiate → Stress-Test.
Composes sub-patterns: parallel → mechanical → sequential → synthesis.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after, after_all
from protocols.stages import (
    parallel_agent_stage,
    mechanical_stage,
    sequential_agent_stage,
    synthesis_stage,
)
from .prompts import (
    DISCOVER_SOLO_PROMPT,
    DISCOVER_PAIR_MERGE_PROMPT,
    DISCOVER_SYNTHESIS_PROMPT,
    ACH_HYPOTHESIS_PROMPT,
    ACH_SYNTHESIS_PROMPT,
    NEGOTIATE_OPENING_PROMPT,
    NEGOTIATE_REVISION_PROMPT,
    NEGOTIATE_SYNTHESIS_PROMPT,
    TEAM_ASSIGNMENT_PROMPT,
    STRESS_RED_PROMPT,
    STRESS_BLUE_PROMPT,
    STRESS_WHITE_PROMPT,
)


AIRPORT_5G_DEF = ProtocolDef(
    protocol_id="airport_5g_pipeline",
    stages=[
        # --- Stage 1: Discover (1-2-4-All) ---
        Stage(
            name="discover_solo",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="solo_ideas",
                prompt_template=DISCOVER_SOLO_PROMPT,
                use_thinking=True,
            ),
        ),
        Stage(
            name="discover_merge",
            trigger=after("solo_ideas"),
            execute=mechanical_stage(
                topic_in="solo_ideas",
                topic_out="pair_merges",
                prompt_template=DISCOVER_PAIR_MERGE_PROMPT,
            ),
        ),
        Stage(
            name="discover_synthesis",
            trigger=after("pair_merges"),
            execute=synthesis_stage(
                topics_in=["solo_ideas", "pair_merges"],
                topic_out="requirements_map",
                prompt_template=DISCOVER_SYNTHESIS_PROMPT,
            ),
        ),
        # --- Stage 2: Diagnose (ACH) ---
        Stage(
            name="ach_evaluate",
            trigger=after("requirements_map"),
            execute=parallel_agent_stage(
                topic_in="requirements_map",
                topic_out="ach_evidence",
                prompt_template=ACH_HYPOTHESIS_PROMPT,
                use_thinking=True,
            ),
        ),
        Stage(
            name="ach_synthesis",
            trigger=after("ach_evidence"),
            execute=synthesis_stage(
                topics_in=["requirements_map", "ach_evidence"],
                topic_out="diagnosis",
                prompt_template=ACH_SYNTHESIS_PROMPT,
            ),
        ),
        # --- Stage 3: Negotiate (Constraint Negotiation) ---
        Stage(
            name="negotiate_opening",
            trigger=after("diagnosis"),
            execute=parallel_agent_stage(
                topic_in="diagnosis",
                topic_out="opening_positions",
                prompt_template=NEGOTIATE_OPENING_PROMPT,
                use_thinking=True,
            ),
        ),
        Stage(
            name="negotiate_revision",
            trigger=after("opening_positions"),
            execute=sequential_agent_stage(
                topic_in="opening_positions",
                topic_out="revised_positions",
                prompt_template=NEGOTIATE_REVISION_PROMPT,
            ),
        ),
        Stage(
            name="negotiate_synthesis",
            trigger=after("revised_positions"),
            execute=synthesis_stage(
                topics_in=["diagnosis", "opening_positions", "revised_positions"],
                topic_out="consensus",
                prompt_template=NEGOTIATE_SYNTHESIS_PROMPT,
            ),
        ),
        # --- Stage 4: Stress-Test (Red/Blue/White) ---
        Stage(
            name="team_assignment",
            trigger=after("consensus"),
            execute=mechanical_stage(
                topic_in="consensus",
                topic_out="teams",
                prompt_template=TEAM_ASSIGNMENT_PROMPT,
            ),
        ),
        Stage(
            name="red_team_attack",
            trigger=after("teams"),
            execute=parallel_agent_stage(
                topic_in="consensus",
                topic_out="attacks",
                prompt_template=STRESS_RED_PROMPT,
                use_thinking=True,
            ),
            agents_filter="@red",
        ),
        Stage(
            name="blue_team_defend",
            trigger=after("attacks"),
            execute=parallel_agent_stage(
                topic_in="attacks",
                topic_out="defenses",
                prompt_template=STRESS_BLUE_PROMPT,
                use_thinking=True,
            ),
            agents_filter="@blue",
        ),
        Stage(
            name="white_team_adjudicate",
            trigger=after("defenses"),
            execute=synthesis_stage(
                topics_in=["consensus", "attacks", "defenses"],
                topic_out="final_recommendation",
                prompt_template=STRESS_WHITE_PROMPT,
            ),
            agents_filter="@white",
        ),
    ],
)
