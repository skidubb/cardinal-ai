"""Stage prompts for P47: Pólya Look-Back Protocol."""

METHOD_ANALYSIS_PROMPT = """\
You are a meta-cognitive analyst evaluating the METHOD used to solve a problem, \
not the answer itself.

Given the original question and the protocol output below, analyze:

1. PROTOCOL FIT — Was {protocol_used} the right protocol for this problem? \
Name at least one alternative protocol that could have been used and why.
2. EFFICIENCY — Could we have reached similar quality with fewer agents or \
fewer rounds? Where was effort wasted?
3. SURPRISE — What was most unexpected in the output? What does that tell us \
about this problem type?

Be specific and critical. Reference concrete parts of the output.

ORIGINAL QUESTION:
{question}

PROTOCOL USED: {protocol_used}

PROTOCOL OUTPUT:
{analysis}
"""

GENERALIZATION_PROMPT = """\
You are a meta-cognitive analyst performing the generalization step of a \
Pólya Look-Back reflection.

Given the method analysis below, identify:

1. GENERALIZATION — What transferable insight emerges? Formulate a routing \
rule: "For problems that are [X], prefer protocol [Y] because [Z]."
2. WEAKNESS — Where was the protocol weakest? What specific modification \
would strengthen it for this problem type?
3. NON-OBVIOUS INSIGHT — What did we learn that wasn't apparent before running \
the protocol? What would we tell someone facing a similar problem?

Be concise and actionable. Focus on what generalizes beyond this specific case.

ORIGINAL QUESTION:
{question}

PROTOCOL USED: {protocol_used}

METHOD ANALYSIS:
{method_analysis}
"""

META_SYNTHESIS_PROMPT = """\
You are a protocol routing expert. Distill the reflection below into a single \
concise routing rule for the protocol router.

Format: "For problems that are [X], prefer protocol [Y] because [Z]."

The rule should be specific enough to be actionable but general enough to apply \
beyond this single case. Output ONLY the routing rule, nothing else.

PROTOCOL USED: {protocol_used}

FULL REFLECTION:
{reflection}
"""
