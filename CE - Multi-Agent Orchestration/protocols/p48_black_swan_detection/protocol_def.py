"""P48 Black Swan Detection — blackboard protocol definition.

5 stages: causal_graph → threshold_scan → confluence → historical_analogues → adversarial_memo.
"""

from __future__ import annotations

from protocols.orchestrator_loop import ProtocolDef, Stage
from protocols.triggers import always, after
from protocols.stages import parallel_agent_stage, mechanical_stage, synthesis_stage
from .prompts import (
    CAUSAL_GRAPH_PROMPT,
    THRESHOLD_SCAN_PROMPT,
    CONFLUENCE_PROMPT,
    HISTORICAL_ANALOGUE_PROMPT,
    ADVERSARIAL_MEMO_PROMPT,
)


P48_DEF = ProtocolDef(
    protocol_id="p48_black_swan_detection",
    stages=[
        Stage(
            name="causal_graph",
            trigger=always(),
            execute=parallel_agent_stage(
                topic_in="question",
                topic_out="causal_graphs",
                prompt_template=CAUSAL_GRAPH_PROMPT,
            ),
        ),
        Stage(
            name="threshold_scan",
            trigger=after("causal_graphs"),
            execute=parallel_agent_stage(
                topic_in="causal_graphs",
                topic_out="threshold_scans",
                prompt_template=THRESHOLD_SCAN_PROMPT,
            ),
        ),
        Stage(
            name="confluence",
            trigger=after("threshold_scans"),
            execute=mechanical_stage(
                topic_in="threshold_scans",
                topic_out="confluences",
                prompt_template=CONFLUENCE_PROMPT,
            ),
        ),
        Stage(
            name="historical_analogues",
            trigger=after("confluences"),
            execute=parallel_agent_stage(
                topic_in="confluences",
                topic_out="historical_analogues",
                prompt_template=HISTORICAL_ANALOGUE_PROMPT,
            ),
        ),
        Stage(
            name="adversarial_memo",
            trigger=after("historical_analogues"),
            execute=synthesis_stage(
                topics_in=[
                    "causal_graphs",
                    "threshold_scans",
                    "confluences",
                    "historical_analogues",
                ],
                topic_out="synthesis",
                prompt_template=ADVERSARIAL_MEMO_PROMPT,
            ),
        ),
    ],
)
