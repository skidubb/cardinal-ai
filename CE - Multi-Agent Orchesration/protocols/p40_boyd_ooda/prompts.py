"""Stage prompts for P40: Boyd OODA Rapid Cycle Protocol."""

OBSERVE_PROMPT = """\
You are in a rapid OODA (Observe-Orient-Decide-Act) cycle. This is the OBSERVE phase.

Speed over completeness. What are the 3 most important new facts about this situation?

Rules:
- Raw observations ONLY. No interpretation, no recommendations.
- Be concrete and specific. Name things, cite numbers, state facts.
- If you see nothing new, say so — do not fabricate.

THE SITUATION:
{question}
{prior_context}
"""

ORIENT_PROMPT = """\
You are in a rapid OODA cycle. This is the ORIENT phase — the critical step.

Given these observations, answer three questions:
1. What mental model are these observations consistent with?
2. What prior model do they BREAK? If they break nothing, you are not looking hard enough.
3. State the updated model in 2-3 sentences.

Do not hedge. Commit to a model. You can revise it next cycle.

OBSERVATIONS:
{observations}
"""

DECIDE_PROMPT = """\
You are in a rapid OODA cycle. This is the DECIDE phase.

Given this mental model, what is the single best action to take RIGHT NOW?

Rules:
- Not the optimal action — the best action executable immediately.
- State it as a clear directive in 1-2 sentences.
- Include who should do it and what the first concrete step is.

CURRENT MODEL:
{model}
"""

ACT_PROMPT = """\
You are in a rapid OODA cycle. This is the ACT phase.

The decision has been made. Now project forward:
1. Restate the decision as a clear action directive.
2. What are the 2-3 most likely immediate consequences of this action?
3. What should the next OBSERVE phase look for to confirm or disconfirm these consequences?

DECISION:
{decision}

ORIGINAL SITUATION:
{question}
"""

SYNTHESIS_PROMPT = """\
You are a strategic advisor reviewing the results of {num_cycles} rapid OODA \
(Observe-Orient-Decide-Act) cycles applied to a strategic situation.

Summarize:
1. **Model Evolution**: How did the mental model change across cycles?
2. **Final Recommendation**: The last cycle's decision, with confidence level.
3. **Key Insight**: The single most important thing learned from cycling rapidly.

Be direct. No filler. The value of OODA is speed — your summary should match.

ORIGINAL SITUATION:
{question}

CYCLE RESULTS:
{cycles_json}
"""
