"""P0c Tiered Escalation — blackboard protocol definition.

Tiered: tier1 single agent → confidence check → tier2 parallel → consensus check →
tier3 debate (rebuttals + oversight).
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import (
    parallel_agent_stage,
    mechanical_stage,
    synthesis_stage,
    sequential_agent_stage,
)
from .prompts import (
    TIER1_AGENT_PROMPT,
    TIER1_CONFIDENCE_PROMPT,
    TIER2_AGENT_PROMPT,
    TIER2_SYNTHESIS_PROMPT,
    TIER3_REBUTTAL_PROMPT,
    TIER3_OVERSIGHT_PROMPT,
)


P0C_DEF = ProtocolDef(
    protocol_id="p0c_tiered_escalation",
    stages=[
        Stage(
            name="tier1_response",
            trigger=always(),
            execute=sequential_agent_stage(
                topic_in="question",
                topic_out="tier1",
                prompt_template=TIER1_AGENT_PROMPT,
            ),
        ),
        Stage(
            name="tier1_confidence",
            trigger=after("tier1"),
            execute=mechanical_stage(
                topic_in="tier1",
                topic_out="tier1_confidence",
                prompt_template=TIER1_CONFIDENCE_PROMPT,
            ),
        ),
        Stage(
            name="tier2_parallel",
            trigger=after("tier1_confidence"),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="tier2_responses",
                prompt_template=TIER2_AGENT_PROMPT,
                use_thinking=True,
            ),
        ),
        Stage(
            name="tier2_synthesis",
            trigger=after("tier2_responses"),
            execute=synthesis_stage(
                topics_in=["tier2_responses"],
                topic_out="tier2_synthesis",
                prompt_template=TIER2_SYNTHESIS_PROMPT,
            ),
        ),
        Stage(
            name="tier3_rebuttals",
            trigger=after("tier2_synthesis"),
            execute=parallel_agent_stage(
                topic_in="tier2_synthesis",
                topic_out="tier3_rebuttals",
                prompt_template=TIER3_REBUTTAL_PROMPT,
                use_thinking=True,
            ),
        ),
        Stage(
            name="tier3_oversight",
            trigger=after("tier3_rebuttals"),
            execute=synthesis_stage(
                topics_in=["tier1", "tier2_synthesis", "tier3_rebuttals"],
                topic_out="final",
                prompt_template=TIER3_OVERSIGHT_PROMPT,
            ),
        ),
    ],
)
