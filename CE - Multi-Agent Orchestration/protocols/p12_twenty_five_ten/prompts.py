"""Stage prompts for P12: 25/10 Crowd Sourcing Protocol."""

IDEA_GENERATION_PROMPT = """\
You are participating in a 25/10 Crowd Sourcing exercise. Write ONE bold, \
actionable idea that addresses the challenge below.

Rules:
- ONE idea only — your single best, boldest recommendation
- Be specific: include what, how, estimated cost/effort, and expected outcome
- Be bold: safe ideas don't win. Push the boundary.
- Write it as an "idea card" — concise enough to evaluate in 30 seconds

Format your response as:
TITLE: [5-10 word title]
IDEA: [2-4 sentences describing the idea with specifics]
BOLD BECAUSE: [1 sentence on why this is a non-obvious or risky choice]

THE CHALLENGE:
{question}
"""

SCORING_PROMPT = """\
You are scoring an anonymous idea card in a 25/10 exercise. You do NOT know \
who wrote this idea. Score it on a 1-5 scale based on:

- **Boldness** (1-5): Is this a genuinely non-obvious, high-upside idea?
- **Feasibility** (1-5): Can this realistically be executed given the constraints?
- **Impact** (1-5): If successful, how much does this move the needle?

Then give an OVERALL score (1-5) that reflects your gut judgment of whether \
this idea deserves to be in the top 25%.

Output as JSON:
{{"boldness": N, "feasibility": N, "impact": N, "overall": N, "one_line_reaction": "..."}}

THE CHALLENGE CONTEXT:
{question}

THE IDEA CARD:
{idea_card}
"""

SYNTHESIS_PROMPT = """\
You are synthesizing the results of a 25/10 Crowd Sourcing exercise — a \
rapid idea generation + blind scoring protocol where agents independently \
generated bold ideas, then cross-scored each other's ideas anonymously over \
multiple rounds.

Using the ranked results below, produce a strategic briefing with:

1. **Top Ideas** (the winners): For each, explain why it scored well and \
   what makes it strategically compelling
2. **Scoring Patterns**: What themes or tensions emerged across the scoring? \
   Where did agents agree/disagree most?
3. **The Bold vs. Safe Spectrum**: Which ideas were scored high on boldness \
   but lower on feasibility? These are worth discussing even if they didn't win.
4. **Recommended Portfolio**: If you could pick 2-3 ideas to pursue as a \
   portfolio (combining different risk profiles), which combination would you \
   recommend and why?

Be strategic, direct, and specific.

THE ORIGINAL CHALLENGE:
{question}

RANKED RESULTS (all ideas with scores):
{ranked_results}
"""
