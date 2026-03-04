"""P20 Borda Count Voting — blackboard protocol definition.

4 stages: ranking → tally (compute) → tiebreak → final_report.
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
    RANKING_PROMPT,
    TIEBREAK_PROMPT,
    FINAL_REPORT_PROMPT,
)


P20_DEF = ProtocolDef(
    protocol_id="p20_borda_count",
    stages=[
        Stage(
            name="ranking",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="ballots",
                prompt_template=RANKING_PROMPT,
            ),
        ),
        Stage(
            name="tally",
            trigger=after("ballots"),
            execute=compute_stage(
                topic_in="ballots",
                topic_out="tallied",
                compute_fn=lambda entries: str(
                    [(e.author, e.content) for e in entries]
                ),
            ),
        ),
        Stage(
            name="tiebreak",
            trigger=after("tallied"),
            execute=mechanical_stage(
                topic_in="tallied",
                topic_out="resolved_ranking",
                prompt_template=TIEBREAK_PROMPT,
            ),
        ),
        Stage(
            name="final_report",
            trigger=after("resolved_ranking"),
            execute=synthesis_stage(
                topics_in=["ballots", "tallied", "resolved_ranking"],
                topic_out="synthesis",
                prompt_template=FINAL_REPORT_PROMPT,
            ),
        ),
    ],
)
