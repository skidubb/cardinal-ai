"""Stage prompts for P33: Goldratt Evaporation Cloud Protocol."""

MAP_CLOUD_PROMPT = """\
You are a conflict resolution specialist using Goldratt's Evaporation Cloud \
(also known as the Conflict Resolution Diagram). Your job is to structure \
the following conflict or contradiction into a precise cloud diagram.

The cloud has 5 elements:
- **Objective**: The common goal both sides share
- **Requirement A**: One need that must be met to achieve the objective
- **Requirement B**: Another need that must be met to achieve the objective
- **Prerequisite A**: The action or condition required to satisfy Requirement A
- **Prerequisite B**: The action or condition required to satisfy Requirement B

The conflict: Prerequisites A and B appear to be INCOMPATIBLE — you cannot \
do both simultaneously.

Output as a JSON object with exactly these keys:
"objective", "requirement_a", "requirement_b", "prerequisite_a", "prerequisite_b"

Each value should be a clear, concise statement (1-2 sentences).

THE CONFLICT/CONTRADICTION:
{question}
"""

ASSUMPTION_PROMPT = """\
You are analyzing one arrow in a Goldratt Evaporation Cloud — a structured \
conflict diagram. Your job is to surface the HIDDEN ASSUMPTIONS that must \
be true for this particular logical link to hold.

The cloud:
- Objective: {objective}
- Requirement A: {requirement_a}
- Requirement B: {requirement_b}
- Prerequisite A: {prerequisite_a}
- Prerequisite B: {prerequisite_b}

You are analyzing the arrow: **{arrow_label}**
Which connects: "{arrow_from}" → "{arrow_to}"

Generate 3-8 hidden assumptions that must be true for this link to hold. \
Each assumption must be:
1. Stated as a testable claim (something that could be verified or falsified)
2. Not obvious or tautological
3. Specific to this particular link, not generic

Output as a JSON array of strings, each being one assumption.
"""

CONFLICT_ASSUMPTION_PROMPT = """\
You are analyzing the CONFLICT ARROW in a Goldratt Evaporation Cloud — the \
incompatibility between the two prerequisites.

The cloud:
- Objective: {objective}
- Requirement A: {requirement_a}
- Requirement B: {requirement_b}
- Prerequisite A: {prerequisite_a}
- Prerequisite B: {prerequisite_b}

The conflict: "{prerequisite_a}" and "{prerequisite_b}" appear incompatible.

Generate 3-8 hidden assumptions that make these prerequisites seem \
incompatible. Each assumption must be:
1. Stated as a testable claim
2. Not obvious or tautological
3. Specific to WHY these two things cannot coexist

Output as a JSON array of strings, each being one assumption.
"""

INJECTION_PROMPT = """\
You are a breakthrough strategist using Goldratt's Evaporation Cloud method. \
You have mapped a conflict and surfaced hidden assumptions behind every arrow. \
Now identify the INJECTION POINT — the single weakest assumption that, if \
invalidated, dissolves the entire contradiction.

The cloud:
- Objective: {objective}
- Requirement A: {requirement_a}
- Requirement B: {requirement_b}
- Prerequisite A: {prerequisite_a}
- Prerequisite B: {prerequisite_b}

Hidden assumptions by arrow:
{assumptions_text}

CRITICAL QUALITY GATE: The solution must NOT be a compromise. It must allow \
BOTH prerequisites to be satisfied (or render the conflict irrelevant). A \
compromise that partially satisfies each side is a FAILURE of this method.

Produce your analysis as a JSON object with these keys:
- "injection_point": The specific assumption you are invalidating (quote it exactly)
- "arrow": Which arrow this assumption belongs to
- "why_weakest": Why this assumption is the most vulnerable (2-3 sentences)
- "solution": What becomes possible once this assumption is removed (2-3 sentences)
- "synthesis": A full analysis (3-5 paragraphs) explaining the cloud, the \
  assumptions, why the injection point was chosen, and the resulting solution. \
  Include how BOTH sides get what they need.
"""
