"""P09 Troika Consulting — blackboard protocol definition.

Rotating client/consultant pattern: client presents → consultant1 advises →
consultant2 builds → consolidate → client reflects → final synthesis.
Sequential within rounds.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import sequential_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    CLIENT_PRESENT_PROMPT,
    CONSULTANT_INITIAL_PROMPT,
    CONSULTANT_RESPOND_PROMPT,
    CONSULTANT_CONSOLIDATE_PROMPT,
    CLIENT_REFLECT_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)


P09_DEF = ProtocolDef(
    protocol_id="p09_troika_consulting",
    stages=[
        Stage(
            name="client_present",
            trigger=always(),
            execute=sequential_agent_stage(
                topic_in="question",
                topic_out="problem_statement",
                prompt_template=CLIENT_PRESENT_PROMPT,
            ),
        ),
        Stage(
            name="consultant1_advise",
            trigger=after("problem_statement"),
            execute=sequential_agent_stage(
                topic_in="problem_statement",
                topic_out="consultant1_response",
                prompt_template=CONSULTANT_INITIAL_PROMPT,
            ),
        ),
        Stage(
            name="consultant2_respond",
            trigger=after("consultant1_response"),
            execute=sequential_agent_stage(
                topic_in="consultant1_response",
                topic_out="consultant2_response",
                prompt_template=CONSULTANT_RESPOND_PROMPT,
            ),
        ),
        Stage(
            name="consolidate",
            trigger=after("consultant2_response"),
            execute=mechanical_stage(
                topic_in="consultant2_response",
                topic_out="consolidated_advice",
                prompt_template=CONSULTANT_CONSOLIDATE_PROMPT,
            ),
        ),
        Stage(
            name="client_reflect",
            trigger=after("consolidated_advice"),
            execute=sequential_agent_stage(
                topic_in="consolidated_advice",
                topic_out="reflection",
                prompt_template=CLIENT_REFLECT_PROMPT,
            ),
        ),
        Stage(
            name="final_synthesis",
            trigger=after("reflection"),
            execute=synthesis_stage(
                topics_in=["problem_statement", "consolidated_advice", "reflection"],
                topic_out="synthesis",
                prompt_template=FINAL_SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
