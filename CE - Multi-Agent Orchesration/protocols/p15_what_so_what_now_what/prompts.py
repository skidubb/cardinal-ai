"""Prompt templates for P15: What / So What / Now What protocol."""

WHAT_PROMPT = """\
You are participating in a structured sensemaking exercise using the \
"What / So What / Now What" framework.

**Question / Situation:**
{question}

**Your task (WHAT phase):**
From your role's perspective, answer: "What happened? What did you observe? \
What are the key facts and data points?"

Be concrete and specific. Report observations, not interpretations. \
Stick to what is observable, measurable, or verifiable. \
Produce 3-7 distinct observations, each with supporting evidence or rationale."""

CONSOLIDATE_OBSERVATIONS_PROMPT = """\
You are a facilitator consolidating observations from multiple participants.

**Original Question:**
{question}

**Individual Observations:**
{observations}

Your task:
1. Group observations into coherent themes.
2. Remove exact duplicates but preserve distinct perspectives on the same topic.
3. Note which agents contributed each observation cluster.
4. Produce a structured summary of all observations organized by theme.

Output a clean, themed summary — not a raw list."""

SO_WHAT_PROMPT = """\
You are participating in a structured sensemaking exercise using the \
"What / So What / Now What" framework.

**Question / Situation:**
{question}

**Consolidated Observations (from all participants):**
{consolidated_observations}

**Your task (SO WHAT phase):**
Now that you see all observations, answer from your role's perspective: \
"Why does this matter? What patterns emerge? What are the implications? \
What are the risks and opportunities?"

Go beyond restating facts. Identify:
- Cause-and-effect relationships
- Emerging patterns or trends
- Second-order consequences
- Risks that need mitigation
- Opportunities that could be seized

Produce 3-7 distinct implications with reasoning."""

CONSOLIDATE_IMPLICATIONS_PROMPT = """\
You are a facilitator consolidating implications from multiple participants.

**Original Question:**
{question}

**Consolidated Observations:**
{consolidated_observations}

**Individual Implications:**
{implications}

Your task:
1. Identify cross-cutting themes in the implications.
2. Note where agents converge (shared concerns) and where they diverge (unique perspectives).
3. Flag high-stakes implications that multiple agents raised.
4. Produce a structured summary of implications organized by theme and urgency.

Output a clean, themed summary highlighting convergence and divergence."""

NOW_WHAT_PROMPT = """\
You are participating in a structured sensemaking exercise using the \
"What / So What / Now What" framework.

**Question / Situation:**
{question}

**Consolidated Observations:**
{consolidated_observations}

**Consolidated Implications:**
{consolidated_implications}

**Your task (NOW WHAT phase):**
Given everything observed and its implications, answer from your role's \
perspective: "What actions should we take? What are the next steps? \
What decisions need to be made?"

Be specific and actionable. For each recommendation:
- State the action clearly
- Identify who should own it
- Suggest a timeframe (immediate / short-term / medium-term)
- Note dependencies or prerequisites

Produce 3-7 concrete action items."""

FINAL_SYNTHESIS_PROMPT = """\
You are producing the final synthesis for a "What / So What / Now What" \
sensemaking exercise.

**Original Question:**
{question}

**Consolidated Observations (WHAT):**
{consolidated_observations}

**Consolidated Implications (SO WHAT):**
{consolidated_implications}

**Individual Action Recommendations (NOW WHAT):**
{now_what_actions}

Your task:
1. Synthesize all three temporal frames into a coherent strategic response.
2. Identify cross-cutting themes that span observations, implications, and actions.
3. Prioritize actions by impact and urgency.
4. Flag any tensions between recommended actions from different perspectives.

Structure your response as:
- **Executive Summary** (2-3 sentences capturing the through-line from observation to action)
- **Key Observations** (the most significant facts, consolidated)
- **Critical Implications** (the highest-stakes "so whats", ranked)
- **Recommended Actions** (prioritized, with owners and timeframes)
- **Cross-Cutting Themes** (patterns that span all three frames)
- **Unresolved Tensions** (where perspectives diverge on action)"""
