"""Prompts for the P11 Discovery & Action Dialogue (DAD) protocol."""

SCOUT_DEVIANTS_PROMPT = """\
You are participating in a Discovery & Action Dialogue — a structured process for \
finding "positive deviants" who succeed despite the same constraints everyone else faces.

**Question / Challenge:**
{question}

Your role: {agent_name}
{system_prompt}

From your role's perspective, identify 3-5 "positive deviants" — specific examples of \
who or what succeeds despite facing the same constraints, resource limitations, or \
environmental pressures that typically cause failure. These can be companies, teams, \
individuals, strategies, products, or practices.

For each deviant, explain the specific BEHAVIOR or PRACTICE that sets them apart — \
not just their outcome, but what they actually DO differently.

Respond in JSON:
{{
  "deviants": [
    {{
      "deviant": "name or description of the positive deviant",
      "behavior": "the specific behavior or practice that sets them apart",
      "why_it_works": "why this behavior produces better outcomes despite shared constraints"
    }}
  ]
}}
"""

FILTER_BEHAVIOR_PROMPT = """\
You are filtering a candidate behavior identified through positive deviance analysis.

**Original Question:**
{question}

**Candidate Behavior:**
Deviant: {deviant}
Behavior: {behavior}
Why it works: {why_it_works}

Evaluate this behavior against THREE criteria:
1. **Uncommon**: Is this behavior genuinely uncommon? (If everyone already does it, it's not a positive deviant behavior.)
2. **Accessible**: Is this behavior accessible and adoptable by others facing the same constraints? (If it requires unique resources or privileges, it fails.)
3. **Evidence**: Is there evidence or a clear causal logic for why this works? (Correlation without mechanism fails.)

Respond in JSON:
{{
  "deviant": "{deviant}",
  "behavior": "{behavior}",
  "uncommon": true or false,
  "uncommon_reasoning": "brief explanation",
  "accessible": true or false,
  "accessible_reasoning": "brief explanation",
  "evidence": true or false,
  "evidence_reasoning": "brief explanation",
  "passes": true or false
}}
"""

EXTRACT_PRACTICES_PROMPT = """\
You are extracting transferable practices from validated positive deviant behaviors.

**Original Question:**
{question}

**Validated Behaviors:**
{behaviors_block}

For each validated behavior, extract the CORE TRANSFERABLE PRACTICE — the underlying \
principle or method that can be adopted by others, stripped of context-specific details.

Group related behaviors into unified practices where appropriate. Aim for 3-7 distinct practices.

Respond in JSON:
{{
  "practices": [
    {{
      "practice": "name of the transferable practice",
      "description": "what to actually do — specific, actionable",
      "derived_from": ["list of deviant names this was extracted from"],
      "mechanism": "why this practice works — the causal logic"
    }}
  ]
}}
"""

ADAPT_RECOMMENDATIONS_PROMPT = """\
You are producing the final synthesis for a Discovery & Action Dialogue.

**Original Question:**
{question}

The following transferable practices were extracted from positive deviant analysis:

{practices_block}

Your task:
1. Adapt these practices into actionable recommendations for the target context.
2. Prioritize by expected impact and ease of adoption.
3. Identify potential barriers to adoption and how to overcome them.
4. Suggest a sequencing strategy — what to try first, what to build toward.

Structure your response as:
- **Executive Summary** (2-3 sentences on what positive deviants reveal about this challenge)
- **Recommended Actions** (ranked, with rationale and adoption guidance)
- **Adoption Barriers & Mitigations** (what could go wrong and how to address it)
- **Implementation Sequence** (what to start with, what to phase in)
"""
