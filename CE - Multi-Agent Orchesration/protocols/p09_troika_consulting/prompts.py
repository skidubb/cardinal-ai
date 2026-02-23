"""Prompt templates for P9: Troika Consulting protocol."""

CLIENT_PRESENT_PROMPT = """\
You are acting as the **Client** in a Troika Consulting session.

Your role perspective: {role_description}

**Question / Challenge:**
{question}

Present the problem from your role's perspective. Be specific about:
1. What the core challenge or decision is
2. What you've already considered or tried
3. Where you feel stuck or uncertain
4. What kind of help would be most valuable

Be candid and detailed — the quality of advice you receive depends on how well \
you frame the problem. Write 2-4 substantive paragraphs."""

CONSULTANT_INITIAL_PROMPT = """\
You are acting as a **Consultant** in a Troika Consulting session. \
The Client has presented a problem and is now SILENT — they are only listening. \
You must speak freely and candidly, as if the Client cannot interrupt.

Your role perspective: {role_description}

**Original Question:**
{question}

**Client's Problem Statement (from {client_name}):**
{problem_statement}

Provide your initial analysis and advice. Consider:
1. What the Client may be missing or underweighting
2. Reframes that could change how they see the problem
3. Specific, actionable recommendations from your expertise area
4. Risks or blind spots you see from your vantage point

Be direct and substantive — the Client benefits most from honest outside perspective."""

CONSULTANT_RESPOND_PROMPT = """\
You are the second **Consultant** in a Troika Consulting session. \
The Client is SILENT and listening. Your fellow consultant has shared their \
initial analysis. Build on it, challenge it where needed, and add your own perspective.

Your role perspective: {role_description}

**Original Question:**
{question}

**Client's Problem Statement (from {client_name}):**
{problem_statement}

**Consultant 1 ({consultant1_name})'s Analysis:**
{consultant1_response}

Respond to Consultant 1's analysis:
1. Where do you agree? What would you reinforce?
2. Where do you disagree or see it differently?
3. What did Consultant 1 miss that your expertise reveals?
4. What additional recommendations would you add?

Then produce a **Consolidated Advice** section that synthesizes both perspectives \
into a coherent set of recommendations for the Client."""

CONSULTANT_CONSOLIDATE_PROMPT = """\
You are a facilitator consolidating the consultation dialogue into clear advice.

**Original Question:**
{question}

**Client ({client_name})'s Problem Statement:**
{problem_statement}

**Consultant 1 ({consultant1_name})'s Initial Analysis:**
{consultant1_response}

**Consultant 2 ({consultant2_name})'s Response & Build:**
{consultant2_response}

Produce a clean, consolidated advisory output:
1. **Key Insights** — The most important observations from both consultants
2. **Recommendations** — Prioritized list of actionable advice
3. **Tensions** — Areas where the consultants disagreed (valuable signal for the Client)
4. **Questions for the Client** — What the Client should reflect on"""

CLIENT_REFLECT_PROMPT = """\
You are the **Client** in a Troika Consulting session. You were SILENT while two \
consultants discussed your problem. Now it's your turn to reflect on what you heard.

Your role perspective: {role_description}

**Original Question:**
{question}

**Your Problem Statement:**
{problem_statement}

**Consolidated Advice from Consultants ({consultant1_name} & {consultant2_name}):**
{consolidated_advice}

Reflect on the consultation:
1. **What resonated** — Which insights or recommendations landed most powerfully?
2. **What surprised you** — What did you not expect to hear?
3. **What you'll adopt** — Specific recommendations you plan to act on
4. **What you still question** — Where you remain unconvinced or need more information
5. **Action plan** — Concrete next steps with your updated thinking

Be honest about what changed your mind and what didn't."""

FINAL_SYNTHESIS_PROMPT = """\
You are producing the final synthesis for a multi-round Troika Consulting session.

**Original Question:**
{question}

Multiple agents each took a turn as Client, receiving advice from different \
consultant pairs. Here are all the round results:

{round_summaries}

Your task:
1. Synthesize insights across all Troika rounds into a coherent strategic response.
2. Identify the highest-conviction recommendations that appeared across multiple rounds.
3. Note where different Client perspectives revealed different facets of the problem.
4. Surface any recurring tensions or unresolved questions.
5. Provide a clear, actionable final recommendation.

Structure your response as:
- **Executive Summary** (2-3 sentences)
- **Cross-Round Insights** (patterns that emerged across multiple consultations)
- **Top Recommendations** (ranked, with rationale)
- **Unresolved Tensions** (areas where rounds diverged)
- **Suggested Next Steps**"""
