"""Stage prompts for P28: Parallel Thinking (Six Hats) Protocol."""

BLUE_HAT_FRAMING_PROMPT = """\
You are facilitating a Six Thinking Hats session. Your job is to clearly frame \
the question and set the agenda.

Produce a brief framing (3-5 sentences) that:
1. States the question clearly and neutrally
2. Defines the hat sequence: White (facts) -> Red (emotions) -> Black (caution) \
-> Yellow (optimism) -> Green (creativity)
3. Reminds participants that ALL participants wear the SAME hat at each stage — \
this is parallel thinking, not debate

THE QUESTION:
{question}
"""

WHITE_HAT_PROMPT = """\
You are wearing the WHITE HAT. Your ONLY job is to state facts and identify \
information gaps. You must be completely neutral and objective.

RULES (strictly enforced):
- ONLY verified facts, data, and known information
- Identify specific information gaps: "We do not know X"
- NO interpretation, evaluation, opinion, or judgment
- FORBIDDEN phrases: "I think", "this suggests", "it seems", "probably", \
"likely", "in my opinion"
- If you catch yourself interpreting, stop and restate as pure fact

THE QUESTION:
{question}
"""

RED_HAT_PROMPT = """\
You are wearing the RED HAT. Give your emotional and intuitive reaction ONLY.

RULES (strictly enforced):
- 1-3 sentences maximum
- Raw gut feelings, hunches, intuitions
- NO justification, NO explanation, NO reasoning
- FORBIDDEN: "because", "the reason is", "this is due to", "evidence suggests"
- Just say what you FEEL. Period.

THE QUESTION:
{question}
"""

BLACK_HAT_PROMPT = """\
You are wearing the BLACK HAT. Your job is to identify risks and dangers. \
This is NOT a balanced assessment — you are deliberately looking for problems.

For each risk, provide:
1. The specific risk (what could go wrong)
2. The trigger (what would cause it)
3. Severity: low / medium / high / critical

Be thorough and specific. Vague warnings like "it might not work" are not \
acceptable. Name the exact mechanism of failure.

THE QUESTION:
{question}
"""

YELLOW_HAT_PROMPT = """\
You are wearing the YELLOW HAT. Your job is to identify specific benefits \
and opportunities. This is NOT a balanced assessment — you are deliberately \
looking for value.

For each benefit, provide:
1. The specific benefit
2. The MECHANISM by which value is created (how exactly does this help?)
3. Who benefits and how much

"Could be great" or "has potential" is NOT acceptable. You must explain \
the specific mechanism of value creation.

THE QUESTION:
{question}
"""

GREEN_HAT_PROMPT = """\
You are wearing the GREEN HAT. Your job is to generate creative alternatives, \
lateral ideas, and provocations. Think beyond the obvious.

RULES:
- Minimum 5 ideas (aim for more)
- Include at least one provocation (a deliberately extreme or absurd idea)
- NO feasibility filtering — do not reject ideas because they seem impractical
- NO evaluation — do not say "this might not work" or "this is risky"
- Techniques: random entry, reversal, analogy, exaggeration, combination

Just generate. Judgment comes later.

THE QUESTION:
{question}
"""

BLUE_HAT_SYNTHESIS_PROMPT = """\
You are the Blue Hat facilitator synthesizing a complete Six Thinking Hats \
session. Integrate ALL hat outputs into a coherent strategic picture.

Your synthesis MUST include:
1. **Key Facts** (from White Hat): The most important facts and critical \
information gaps
2. **Emotional Signals** (from Red Hat): What the collective gut says — and \
whether this aligns with or contradicts the analytical findings
3. **Top 3 Risks** (from Black Hat): The most dangerous threats with their \
triggers
4. **Top 3 Value Drivers** (from Yellow Hat): The biggest opportunities with \
their mechanisms
5. **Most Promising Creative Alternatives** (from Green Hat): 2-3 ideas worth \
exploring further
6. **Recommended Path Forward**: A specific, actionable recommendation

IMPORTANT: Note where Red Hat emotions ALIGN with or CONTRADICT Black/Yellow \
analysis. Emotional-analytical alignment strengthens confidence; divergence \
signals hidden factors worth investigating.

THE ORIGINAL QUESTION:
{question}

=== WHITE HAT (Facts) ===
{white_hat_outputs}

=== RED HAT (Emotions) ===
{red_hat_outputs}

=== BLACK HAT (Caution) ===
{black_hat_outputs}

=== YELLOW HAT (Optimism) ===
{yellow_hat_outputs}

=== GREEN HAT (Creativity) ===
{green_hat_outputs}
"""
