"""P35 Simon Satisficing — blackboard protocol definition.

4 stages: threshold → generate_evaluate_loop (multi-round) → synthesize.
The multi-round stage generates and evaluates options until one is accepted.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import mechanical_stage, multi_round_stage, synthesis_stage
from .prompts import (
    THRESHOLD_PROMPT,
    GENERATE_OPTION_PROMPT,
    EVALUATE_OPTION_PROMPT,
    SYNTHESIS_PROMPT,
)


def _satisfice_converged(bb, round_num):
    """Stop iterating if an option was accepted."""
    entries = bb.read(f"satisfice_round_{round_num - 1}")
    return any("ACCEPT" in str(e.content) for e in entries)


P35_DEF = ProtocolDef(
    protocol_id="p35_satisficing",
    stages=[
        Stage(
            name="threshold",
            trigger=always(),
            execute=mechanical_stage(
                topic_in="question",
                topic_out="criteria",
                prompt_template=THRESHOLD_PROMPT,
            ),
        ),
        Stage(
            name="generate_evaluate_loop",
            trigger=after("criteria"),
            execute=multi_round_stage(
                topic_base="satisfice",
                prompt_template=GENERATE_OPTION_PROMPT,
                max_rounds=5,
                convergence_fn=_satisfice_converged,
            ),
        ),
        Stage(
            name="synthesize",
            trigger=after("satisfice_complete"),
            execute=synthesis_stage(
                topics_in=["criteria", "satisfice_round_1"],
                topic_out="synthesis",
                prompt_template=SYNTHESIS_PROMPT,
            ),
        ),
    ],
)
