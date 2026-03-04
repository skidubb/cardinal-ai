"""P43 Leibniz Auditable Chain — blackboard protocol definition.

3 stages: decompose → audit → verdict.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage, parallel_agent_stage, synthesis_stage
from .prompts import (
    DECOMPOSE_PROMPT,
    AUDIT_PROMPT,
    VERDICT_PROMPT,
)


P43_DEF = ProtocolDef(
    protocol_id="p43_leibniz_audit",
    stages=[
        Stage(
            name="decompose",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="steps_json",
                prompt_template=DECOMPOSE_PROMPT,
            ),
        ),
        Stage(
            name="audit",
            trigger=after("steps_json"),
            execute=parallel_agent_stage(
                topic_in="steps_json",
                topic_out="findings_json",
                prompt_template=AUDIT_PROMPT,
            ),
        ),
        Stage(
            name="verdict",
            trigger=after("findings_json"),
            execute=synthesis_stage(
                topics_in=["steps_json", "findings_json"],
                topic_out="synthesis",
                prompt_template=VERDICT_PROMPT,
            ),
        ),
    ],
)
