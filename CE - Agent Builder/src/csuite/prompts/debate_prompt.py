"""
Debate prompt templates for multi-round executive debates.

Controls agent behavior across debate rounds: opening positions, rebuttals,
final statements, and post-debate synthesis.
"""

from csuite.session import DebateArgument

DEBATE_OPENING_INSTRUCTIONS = """You are participating in a structured executive debate.

**ROUND 1 — OPENING POSITION**

Present your strongest position on the question below from your executive \
perspective. Be specific and take a clear stance. Disagreement with other \
executives is expected and encouraged.

- Lead with your top-line recommendation
- Support with 2-3 concrete arguments from your domain expertise
- Identify the key risk or trade-off from your perspective
- Be direct — hedge later if the evidence warrants it

Do NOT try to cover all perspectives. Own YOUR lane and argue it forcefully.
"""


DEBATE_REBUTTAL_INSTRUCTIONS = """You are participating in a structured executive debate.

**ROUND {round_number} of {total_rounds} — REBUTTAL**

You have seen arguments from the prior round(s). Now respond directly.

{prior_arguments}

**Your task:**
- Directly address specific points made by other executives — name them
- Where you agree, say so explicitly and explain why
- Where you disagree, challenge their reasoning with evidence from your domain
- Introduce new evidence or considerations that strengthen your position
- If another executive changed your mind on something, concede it clearly

Do NOT repeat your opening. Build on it, adjust it, or defend it.
"""


DEBATE_FINAL_INSTRUCTIONS = """You are participating in a structured executive debate.

**ROUND {round_number} of {total_rounds} — FINAL STATEMENT**

This is the last round. Here is the full debate history:

{prior_arguments}

**Your task:**
- State any concessions you are making based on the debate
- Identify your remaining disagreements and why they matter
- Assign a confidence level (1-10) to your overall recommendation
- Provide your single most important recommended action
- Be honest about what you got wrong or what surprised you

This is your final word. Make it count.
"""


DEBATE_SYNTHESIS_PROMPT = """\
You are synthesizing a multi-round executive debate \
for a professional services firm.

Unlike a standard synthesis from parallel perspectives, this debate \
involved genuine back-and-forth argumentation. Executives challenged \
each other, made concessions, and evolved their positions across rounds.

Your synthesis must account for this evolution:

## Debate Synthesis

### Verdict
[1-2 sentences: what did this debate resolve?]

### Convergence Points
[Where did the executives converge through debate? \
What positions survived cross-examination?]

### Surviving Arguments
[Which arguments held up under challenge? Cite specific exchanges.]

### Concessions Made
[What did executives concede during the debate? \
These are often the most valuable insights.]

### Remaining Fault Lines
[Where do genuine disagreements persist? Why couldn't they be resolved?]

### Recommended Path Forward
[Specific, prioritized actions that account for the full debate \
— not just the loudest voice.]

### Confidence Assessment
[How much confidence should leadership place in this recommendation? \
What would change the answer?]

Be direct. The value of debate over synthesis is that weak arguments \
get exposed. Surface that.
"""


NEGOTIATION_OPENING_INSTRUCTIONS = """You are participating in a structured executive negotiation.

**ROUND 1 — OPENING PROPOSAL + CONSTRAINTS**

Present your plan for the question below from your executive perspective. Be specific.

In addition to your plan, you MUST explicitly declare your constraints — requirements \
that other executives' plans must respect. For each constraint, state:
- What the constraint is
- Whether it is HARD (non-negotiable) or SOFT (preferred)
- A specific value or threshold if applicable

Format your constraints clearly under a "## My Constraints" heading.

Do NOT try to cover all perspectives. Own YOUR lane and propose forcefully.
"""


NEGOTIATION_REBUTTAL_INSTRUCTIONS = """You are participating in a structured executive negotiation.

**ROUND {round_number} of {total_rounds} — REVISION**

You have seen proposals and constraints from all peers.

{prior_arguments}

**Peer Constraints You Must Address:**
{peer_constraints}

**Your task:**
- Review all HARD constraints from peers — your revised plan MUST satisfy them
- For SOFT constraints, satisfy them where possible or explain why not
- If a peer constraint conflicts with your own, negotiate: propose a compromise
- Explicitly state which constraints you are satisfying and how
- If you cannot satisfy a HARD constraint, explain why and propose an alternative

Format your response with:
## Revised Plan
[Your updated plan]

## Constraint Compliance
[For each peer HARD constraint, state: satisfied/violated and how]
"""


def format_prior_arguments(arguments: list[DebateArgument]) -> str:
    """Format debate argument history grouped by round for injection into prompts."""
    if not arguments:
        return "_No prior arguments._"

    rounds: dict[int, list[DebateArgument]] = {}
    for arg in arguments:
        rounds.setdefault(arg.round_number, []).append(arg)

    parts: list[str] = []
    for round_num in sorted(rounds.keys()):
        parts.append(f"### Round {round_num}")
        for arg in rounds[round_num]:
            parts.append(f"\n**{arg.agent_name}:**\n{arg.content}\n")

    return "\n".join(parts)
