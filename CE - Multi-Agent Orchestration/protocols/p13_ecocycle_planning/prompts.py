"""Prompt templates for P13: Ecocycle Planning protocol."""

ASSESS_INITIATIVES_PROMPT = """\
You are participating in an Ecocycle Planning exercise — a portfolio lifecycle assessment.

**Context / Strategic Question:**
{question}

**Your role:** {agent_name}
{system_prompt}

**Initiatives to assess:**
{initiatives_block}

For EACH initiative, assign it to exactly one lifecycle stage:
- **birth**: Early-stage — needs investment, protection, and nurturing to grow
- **maturity**: Established — optimize, scale, and extract maximum value
- **destruction**: Declining — sunset gracefully, harvest learnings, free up resources
- **renewal**: Stagnant or ripe for reinvention — experiment, pivot, repurpose

Provide specific reasoning from your role's perspective for each assignment.

Respond in JSON:
{{
  "assessments": [
    {{"initiative": "initiative name exactly as given", "stage": "birth|maturity|destruction|renewal", "reasoning": "brief role-specific justification"}}
  ]
}}
"""

RESOLVE_CONTESTED_PROMPT = """\
You are a facilitator resolving a contested lifecycle stage assignment in an Ecocycle Planning exercise.

**Context / Strategic Question:**
{question}

**Initiative:** {initiative}

**Agent votes:**
{votes_block}

The agents disagree on which lifecycle stage this initiative belongs to. \
Review their reasoning and determine the most appropriate stage assignment.

Consider:
1. Which arguments are most evidence-based vs. speculative?
2. Which stage assignment would lead to the best resource allocation decision?
3. Is there a synthesis position that accounts for the strongest arguments?

Respond in JSON:
{{
  "stage": "birth|maturity|destruction|renewal",
  "reasoning": "brief explanation of why this stage was chosen over alternatives"
}}
"""

ACTION_PLAN_PROMPT = """\
You are generating stage-appropriate strategic actions for an Ecocycle Planning exercise.

**Context / Strategic Question:**
{question}

**Portfolio assignments:**
{portfolio_block}

For EACH initiative, generate 3-5 concrete actions appropriate to its lifecycle stage:
- **Birth** initiatives: invest, protect, allocate dedicated resources, set milestones, reduce bureaucratic friction
- **Maturity** initiatives: optimize processes, scale operations, improve margins, document best practices, defend market position
- **Destruction** initiatives: sunset gracefully, harvest learnings, reassign talent, communicate transition, extract residual value
- **Renewal** initiatives: experiment with pivots, run small bets, cross-pollinate ideas, challenge assumptions, prototype alternatives

Also produce a 2-3 sentence portfolio summary assessing the overall health and balance of the portfolio.

Respond in JSON:
{{
  "action_plans": {{
    "Initiative Name": [
      "action 1",
      "action 2",
      "action 3"
    ]
  }},
  "portfolio_summary": "2-3 sentence assessment of portfolio health, balance across stages, and key risks"
}}
"""
