"""P34 Goldratt Current Reality Tree — blackboard protocol definition.

4 stages: ude_generation → causal_chain → logic_audit → synthesize.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    UDE_GENERATION_PROMPT,
    CAUSAL_CHAIN_PROMPT,
    LOGIC_AUDIT_PROMPT,
    SYNTHESIS_PROMPT,
)


P34_DEF = ProtocolDef(
    protocol_id="p34_current_reality_tree",
    stages=[
        Stage(
            name="ude_generation",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="all_udes",
                prompt_template=UDE_GENERATION_PROMPT,
            ),
        ),
        Stage(
            name="causal_chain",
            trigger=after("all_udes"),
            execute=mechanical_stage(
                topic_in="all_udes",
                topic_out="causal_tree",
                prompt_template=CAUSAL_CHAIN_PROMPT,
            ),
        ),
        Stage(
            name="logic_audit",
            trigger=after("causal_tree"),
            execute=parallel_agent_stage(
                topic_in="causal_tree",
                topic_out="logic_audit",
                prompt_template=LOGIC_AUDIT_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("logic_audit"),
            execute=synthesis_stage(
                topics_in=["causal_tree", "logic_audit"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
