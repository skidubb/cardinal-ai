"""Stage prompts for P36: Peirce Abduction Cycle."""

ABDUCTION_PROMPT = """\
You are participating in a Peirce Abduction Cycle — a structured reasoning \
method that starts from a surprising observation and works backward to the \
best explanation.

PHASE 1: ABDUCTION — "What would make this unsurprising?"

Given the anomaly or surprising observation below, generate 2-3 hypotheses \
that, if true, would make this observation EXPECTED rather than surprising.

Requirements for each hypothesis:
- It must be FALSIFIABLE (there must be a way to prove it wrong)
- It must be NON-OBVIOUS (not the first thing anyone would think of)
- It must EXPLAIN the observation (if the hypothesis is true, the observation follows logically)

For each hypothesis, provide:
1. A clear statement of the hypothesis
2. Why it would make the observation unsurprising
3. What would need to be true for this hypothesis to hold

THE ANOMALY/OBSERVATION:
{anomaly}
"""

DEDUCTION_PROMPT = """\
You are participating in a Peirce Abduction Cycle.

PHASE 2: DEDUCTION — Derive testable predictions from hypotheses.

For each hypothesis below, derive 2-3 testable predictions. Each prediction \
must:
- Follow LOGICALLY from the hypothesis (if H is true, then P must also be true)
- Be OBSERVABLE or MEASURABLE (someone could check whether it holds)
- Be SPECIFIC enough to actually test (not vague or unfalsifiable)

Format each prediction as: "If [hypothesis] is true, then we should observe [specific prediction]."

THE ANOMALY:
{anomaly}

THE HYPOTHESES:
{hypotheses}
"""

INDUCTION_PROMPT = """\
You are participating in a Peirce Abduction Cycle.

PHASE 3: INDUCTION — Test predictions against available evidence.

For each prediction below, assess it against what you know and can reason \
about. Classify each prediction as:
- CONFIRMED: Evidence supports this prediction
- DISCONFIRMED: Evidence contradicts this prediction
- UNTESTABLE: Cannot be assessed with available information

Then provide an overall assessment of each hypothesis:
- Which hypotheses SURVIVE (predictions mostly confirmed or untestable)?
- Which hypotheses are ELIMINATED (key predictions disconfirmed)?

Be rigorous. A single disconfirmed critical prediction can eliminate a hypothesis.

THE ANOMALY:
{anomaly}

THE HYPOTHESES:
{hypotheses}

THE PREDICTIONS:
{predictions}
"""

LOOP_DECISION_PROMPT = """\
You are a logic analyst assessing the results of an abduction-deduction-induction cycle.

Based on the evidence assessment below, determine the outcome:

1. ACCEPT — A hypothesis survives with strong support (most predictions confirmed, \
none critically disconfirmed). State which hypothesis is accepted.
2. CONTINUE — All hypotheses are weakened or eliminated. The disconfirming evidence \
itself becomes a NEW anomaly for the next cycle. State the new anomaly clearly.

Respond with a JSON object:
{{"outcome": "ACCEPT" or "CONTINUE", "reasoning": "...", "accepted_hypothesis": "..." or null, "new_anomaly": "..." or null}}

THE ORIGINAL ANOMALY:
{anomaly}

EVIDENCE ASSESSMENT:
{evidence_assessment}
"""

SYNTHESIS_PROMPT = """\
You are a strategic analyst synthesizing the results of a Peirce Abduction \
Cycle — a structured reasoning method that iteratively generates hypotheses, \
derives predictions, and tests them against evidence.

Produce a final briefing with:

1. **The Anomaly**: What surprising observation triggered the investigation
2. **Investigation Summary**: How many cycles were needed and why
3. **Best Explanation**: The surviving hypothesis (or why none survived)
4. **Key Evidence**: The most important confirming/disconfirming evidence found
5. **Confidence Assessment**: How confident should we be in this explanation?
6. **Remaining Uncertainties**: What we still don't know
7. **Recommended Next Steps**: What to do with this finding

Be direct, specific, and rigorous. No filler.

THE ORIGINAL ANOMALY:
{question}

CYCLE HISTORY:
{cycle_history}
"""
