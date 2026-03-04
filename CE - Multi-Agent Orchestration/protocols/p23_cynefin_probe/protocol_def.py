"""P23 Cynefin Probe — blackboard protocol definition."""
from __future__ import annotations
from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    DOMAIN_CLASSIFICATION_PROMPT,
    COMPLEX_RESPONSE_PROMPT,
    SYNTHESIS_PROMPT,
)

P23_DEF = ProtocolDef(
    protocol_id="p23_cynefin_probe",
    stages=[
        Stage(
            name="classify",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="classifications",
                prompt_template=DOMAIN_CLASSIFICATION_PROMPT,
            ),
        ),
        Stage(
            name="domain_responses",
            trigger=after("classifications"),
            execute=mechanical_stage(
                topic_in="classifications",
                topic_out="domain_responses",
                prompt_template=COMPLEX_RESPONSE_PROMPT,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("domain_responses"),
            execute=synthesis_stage(
                topics_in=["domain_responses"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
