"""Stage prompts for P37: Hegel Sublation Synthesis."""

THESIS_PROMPT = """\
You are presenting the THESIS position in a Hegelian dialectic.

Your job: argue the strongest possible case for Position A. You are an advocate, \
not a balanced analyst. Present this position as if your life depends on it.

For your argument, identify and articulate:
1. **Core Principle**: The fundamental truth this position rests on
2. **Protected Value**: What this position safeguards that matters
3. **Expressed Truth**: The deepest insight this position contains
4. **Full Argument**: The strongest, most compelling case for this position

Do NOT hedge, qualify, or acknowledge the other side. Argue FOR this position \
on its own terms with full conviction.

THE TENSION/CONFLICT:
{question}

POSITION A (your position to defend):
{position_a}
"""

ANTITHESIS_PROMPT = """\
You are presenting the ANTITHESIS position in a Hegelian dialectic.

Your job: argue the strongest possible case for Position B. You are an advocate, \
not a balanced analyst. Present this position as if your life depends on it.

IMPORTANT: Do NOT argue against the Thesis. Argue FOR the Antithesis on its own \
terms. The Thesis has already been presented — you do not need to rebut it. \
Build your own case from the ground up.

For your argument, identify and articulate:
1. **Core Principle**: The fundamental truth this position rests on
2. **Protected Value**: What this position safeguards that matters
3. **Expressed Truth**: The deepest insight this position contains
4. **Full Argument**: The strongest, most compelling case for this position

Do NOT hedge, qualify, or acknowledge the other side.

THE TENSION/CONFLICT:
{question}

POSITION B (your position to defend):
{position_b}

For context, the Thesis argument was:
{thesis}
"""

SUBLATION_PROMPT = """\
You are performing Hegelian SUBLATION (aufheben) — the simultaneous preservation, \
negation, and transcendence of two opposing positions.

This is NOT "split the difference." This is NOT compromise. This is NOT "some of \
A and some of B." You must reach a higher level of abstraction that neither \
original position had access to.

You must satisfy ALL THREE requirements of aufheben:

1. **PRESERVE** (what is TRUE):
   - Name what is TRUE in the Thesis. Retain it.
   - Name what is TRUE in the Antithesis. Retain it.

2. **NEGATE** (what is FALSE or incomplete):
   - Name what is FALSE or incomplete in the Thesis. Correct it.
   - Name what is FALSE or incomplete in the Antithesis. Correct it.

3. **TRANSCEND** (the higher synthesis):
   - State the synthesis as a position NEITHER original position had access to.
   - It must operate at a demonstrably higher level of abstraction.
   - It must NOT be describable as "some of A and some of B."

QUALITY GATES (you must pass all three):
- Aufheben Test: You explicitly preserve, negate, and transcend. All three named.
- Abstraction Test: Your synthesis operates at a higher level than either original.
- Non-Compromise Test: If your synthesis is a middle ground, REJECT it and try again.

THE TENSION/CONFLICT:
{question}

THESIS:
{thesis}

ANTITHESIS:
{antithesis}

Provide your response in these sections:
## Preserved from Thesis
## Preserved from Antithesis
## Negated from Thesis
## Negated from Antithesis
## The Transcendent Synthesis
## Final Synthesis Statement
"""
