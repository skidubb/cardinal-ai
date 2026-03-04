"""P19 Vickrey Auction — blackboard protocol definition.

4 stages: sealed_bids → rank_bids (compute) → calibrated_justification → final_assessment.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import (
    parallel_agent_stage,
    compute_stage,
    mechanical_stage,
    synthesis_stage,
)
from .prompts import (
    SEALED_BID_PROMPT,
    CALIBRATED_JUSTIFICATION_PROMPT,
    FINAL_ASSESSMENT_PROMPT,
)


P19_DEF = ProtocolDef(
    protocol_id="p19_vickrey_auction",
    stages=[
        Stage(
            name="sealed_bids",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="bids",
                prompt_template=SEALED_BID_PROMPT,
            ),
        ),
        Stage(
            name="rank_bids",
            trigger=after("bids"),
            execute=compute_stage(
                topic_in="bids",
                topic_out="ranked_bids",
                compute_fn=lambda entries: str(sorted(
                    [(e.author, e.content) for e in entries],
                    key=lambda x: len(x[1]),
                    reverse=True,
                )),
            ),
        ),
        Stage(
            name="calibrated_justification",
            trigger=after("ranked_bids"),
            execute=mechanical_stage(
                topic_in="ranked_bids",
                topic_out="calibrated",
                prompt_template=CALIBRATED_JUSTIFICATION_PROMPT,
            ),
        ),
        Stage(
            name="final_assessment",
            trigger=after("calibrated"),
            execute=synthesis_stage(
                topics_in=["bids", "ranked_bids", "calibrated"],
                topic_out="synthesis",
                prompt_template=FINAL_ASSESSMENT_PROMPT,
            ),
        ),
    ],
)
