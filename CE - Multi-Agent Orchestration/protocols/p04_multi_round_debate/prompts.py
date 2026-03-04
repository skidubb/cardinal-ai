"""Stage prompts for P4: Multi-Round Debate Protocol."""

OPENING_PROMPT = """\
You are participating in a structured multi-perspective debate on the \
following question. State your position clearly, with supporting reasoning \
and evidence. Be direct and specific.

QUESTION:
{question}"""

REBUTTAL_PROMPT = """\
You are in round {round_number} of a structured debate. Below are the \
arguments from all participants in previous rounds. Review them carefully, then:

1. Acknowledge the strongest points from other perspectives
2. Challenge weak reasoning or unsupported claims
3. Refine and strengthen your own position based on new information
4. Identify areas of emerging agreement or persistent disagreement

Be substantive — don't repeat yourself. Evolve your thinking.

QUESTION:
{question}

PRIOR ARGUMENTS:
{prior_arguments}"""

FINAL_PROMPT = """\
This is the final round of the debate. Below are all prior arguments. \
Produce your final statement:

1. Your **refined position** (may have evolved from your opening)
2. **Key concessions** — what other perspectives convinced you of
3. **Remaining disagreements** — where you still diverge and why
4. **Confidence level** (high/medium/low) in your final position

QUESTION:
{question}

PRIOR ARGUMENTS:
{prior_arguments}"""

SYNTHESIS_PROMPT = """\
You are synthesizing a structured multi-round debate between specialists. \
Below is the full transcript across all rounds.

Produce a synthesis that:
1. **Verdict**: The best-supported answer to the question
2. **Reasoning**: How the debate evolved and which arguments were strongest
3. **Points of Agreement**: What all or most participants converged on
4. **Unresolved Tensions**: Genuine disagreements that remain
5. **Recommendations**: Concrete next steps based on the debate outcome

Be direct. Reference specific arguments and how positions shifted across rounds.

QUESTION:
{question}

FULL DEBATE TRANSCRIPT:
{transcript}"""


def format_prior_arguments(rounds: list) -> str:
    """Format prior debate rounds for inclusion in prompts."""
    sections = []
    for rnd in rounds:
        round_label = f"--- Round {rnd.round_number} ({rnd.round_type}) ---"
        args = "\n\n".join(
            f"[{arg.name}]:\n{arg.content}" for arg in rnd.arguments
        )
        sections.append(f"{round_label}\n{args}")
    return "\n\n".join(sections)
