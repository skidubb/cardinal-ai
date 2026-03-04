"""Prompt templates for P14: 1-2-4-All protocol."""

SOLO_IDEATION_PROMPT = """\
You are participating in a structured ideation exercise.

**Question / Challenge:**
{question}

Generate your best ideas, insights, and recommendations from your role's perspective. \
Think independently — do not hedge or try to anticipate what others might say. \
Be specific, bold, and substantive.

Produce a numbered list of 3-7 distinct ideas with a brief rationale for each."""

PAIR_MERGE_PROMPT = """\
You are a facilitator merging two participants' independent ideas into a shared output.

**Original Question:**
{question}

**Participant A's Ideas:**
{ideas_a}

**Participant B's Ideas:**
{ideas_b}

Your task:
1. Identify shared themes and areas of agreement.
2. Surface productive tensions or complementary perspectives.
3. Resolve conflicts by finding higher-order framing where possible.
4. Produce a single merged list of 4-8 refined ideas, noting which originated from A, B, or emerged from synthesis.

Output a numbered list with brief rationale for each merged idea."""

QUAD_MERGE_PROMPT = """\
You are a facilitator merging two pair-level outputs into a refined group position.

**Original Question:**
{question}

**Pair 1 Output:**
{ideas_a}

**Pair 2 Output:**
{ideas_b}

Your task:
1. Identify the strongest ideas that survived pair-level scrutiny.
2. Look for patterns and higher-order themes across both pairs.
3. Prioritize: rank ideas by strategic impact and feasibility.
4. Eliminate redundancy while preserving nuance.
5. Produce a ranked list of 5-8 refined recommendations.

Output a prioritized numbered list with brief rationale for each."""

FINAL_SYNTHESIS_PROMPT = """\
You are producing the final synthesis for a 1-2-4-All ideation exercise.

**Original Question:**
{question}

The following outputs emerged from progressive small-group merging (solo → pairs → quads):

{quad_outputs}

Your task:
1. Synthesize all group outputs into a coherent strategic response.
2. Identify the highest-conviction ideas that survived multiple rounds of scrutiny.
3. Note any productive tensions that remain unresolved — these are features, not bugs.
4. Provide a clear, actionable final recommendation.

Structure your response as:
- **Executive Summary** (2-3 sentences)
- **Top Recommendations** (ranked, with rationale)
- **Unresolved Tensions** (if any — areas where groups diverged)
- **Suggested Next Steps**"""
