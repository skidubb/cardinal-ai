"""Stage prompts for P5: Constraint Negotiation Protocol."""

OPENING_PROMPT = """\
You are participating in a constraint-based negotiation on the following question. \
In your opening proposal:

1. **State your position** — what you recommend and why
2. **Declare your constraints** — be explicit about what you consider:
   - HARD constraints (non-negotiable requirements you cannot compromise on)
   - SOFT constraints (preferences you'd like but can trade)
3. **Provide reasoning** for each constraint

Be specific with numbers, timelines, and thresholds where possible.

QUESTION:
{question}"""

REVISION_PROMPT = """\
You are in round {round_number} of a constraint-based negotiation. Below are \
the constraints declared by all other participants. You MUST satisfy all HARD \
constraints from peers — these are non-negotiable. You MAY trade SOFT constraints.

Review the peer constraints, then:
1. **Revise your proposal** to satisfy all HARD constraints
2. **Explain trade-offs** — what you changed and why
3. **Update your constraints** — you may add, relax, or tighten constraints based on what you've learned
4. **Flag conflicts** — if any HARD constraints are mutually exclusive, say so explicitly

QUESTION:
{question}

PEER CONSTRAINTS:
{peer_constraints}

PRIOR ARGUMENTS:
{prior_arguments}"""

SYNTHESIS_PROMPT = """\
You are synthesizing the outcome of a constraint-based negotiation between \
specialists. Each participant declared constraints (hard and soft), then \
iteratively revised proposals to satisfy each other's hard constraints.

Using the full negotiation transcript and constraint table below, produce:

1. **Negotiated Outcome**: The proposal that best satisfies all hard constraints
2. **Constraint Satisfaction Matrix**: Which constraints were satisfied, partially \
   satisfied, or violated — and by whom
3. **Key Trade-offs**: What was traded to reach agreement
4. **Remaining Conflicts**: Any hard constraints that could not be simultaneously satisfied
5. **Recommendations**: The path forward based on the negotiation

QUESTION:
{question}

CONSTRAINT TABLE:
{constraint_table}

FULL NEGOTIATION TRANSCRIPT:
{transcript}"""
