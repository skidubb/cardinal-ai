"""Prompts for the P17 Red/Blue/White Team protocol."""

RED_ATTACK_PROMPT = """\
You are a RED TEAM analyst conducting adversarial stress-testing of a proposed plan.

Your role: {agent_name}
{system_prompt}

## Strategic Question
{question}

## Plan Under Review
{plan}

Your job is to ATTACK this plan. Identify vulnerabilities, failure modes, blind spots, \
hidden risks, flawed assumptions, and scenarios where this plan breaks down. Be thorough \
and adversarial — your goal is to find every weakness before reality does.

Think from your domain perspective. What could go wrong in your area of expertise? \
What has the plan failed to consider? What second-order effects could derail execution?

Respond in JSON:
{{
  "agent": "{agent_name}",
  "vulnerabilities": [
    {{
      "id": "V1",
      "category": "category (e.g. Financial Risk, Technical Feasibility, Market Dynamics, Operational Gaps, Competitive Response, Regulatory, Talent, Timing)",
      "title": "short title",
      "severity": "Critical|High|Medium|Low",
      "description": "detailed description of the vulnerability",
      "failure_scenario": "concrete scenario where this vulnerability causes plan failure"
    }}
  ]
}}

Identify 3-5 vulnerabilities, prioritized by severity. Be specific and concrete — \
vague risks are not useful.
"""

BLUE_DEFENSE_PROMPT = """\
You are a BLUE TEAM defender tasked with strengthening a proposed plan against identified attacks.

Your role: {agent_name}
{system_prompt}

## Strategic Question
{question}

## Plan Under Review
{plan}

## Red Team Attacks
The following vulnerabilities have been identified by the Red Team:

{attacks_block}

Your job is to DEFEND the plan. For each vulnerability, provide mitigations, \
counterarguments, evidence that the risk is manageable, or concrete modifications \
to the plan that would address the concern. Be rigorous — hand-waving is not defense.

Think from your domain perspective. What resources, capabilities, or strategies \
can address these vulnerabilities? What precedents suggest the risks are overstated?

Respond in JSON:
{{
  "agent": "{agent_name}",
  "mitigations": [
    {{
      "vulnerability_id": "V1",
      "defense_type": "Mitigation|Counterargument|Plan Modification|Risk Acceptance",
      "response": "detailed defense or mitigation strategy",
      "evidence": "supporting evidence, precedents, or data points",
      "residual_risk": "any remaining risk after this defense is applied"
    }}
  ]
}}

Address EVERY vulnerability listed above. If a vulnerability is genuinely undefendable, \
say so honestly and propose a risk-acceptance rationale.
"""

WHITE_ADJUDICATE_PROMPT = """\
You are the WHITE TEAM arbiter adjudicating a Red/Blue team exercise.

## Strategic Question
{question}

## Plan Under Review
{plan}

## Red Team Attacks
{attacks_block}

## Blue Team Defenses
{defenses_block}

For EACH vulnerability raised by the Red Team, evaluate whether the Blue Team's \
defense is adequate. You must be impartial — neither reflexively siding with attackers \
nor defenders.

Categorize each as:
- **Resolved**: The defense fully addresses the vulnerability. The risk is adequately mitigated.
- **Partially Resolved**: The defense addresses some concerns but gaps remain. Additional action needed.
- **Open**: The defense is inadequate. This remains an active risk requiring attention.

Respond in JSON:
{{
  "adjudications": [
    {{
      "vulnerability_id": "V1",
      "vulnerability_title": "title from Red Team",
      "severity": "Critical|High|Medium|Low",
      "verdict": "Resolved|Partially Resolved|Open",
      "reasoning": "detailed reasoning for the verdict — what was convincing, what fell short",
      "defense_gaps": "specific gaps in the defense, if any",
      "recommended_action": "what should be done next, if anything"
    }}
  ]
}}
"""

FINAL_ASSESSMENT_PROMPT = """\
You are the WHITE TEAM lead producing the final assessment of a Red/Blue/White team exercise.

## Strategic Question
{question}

## Plan Under Review
{plan}

## Adjudication Results
{adjudication_block}

Synthesize the full exercise into a final risk assessment and set of recommendations.

Respond in JSON:
{{
  "resolved_risks": [
    {{"vulnerability_id": "V1", "title": "title", "summary": "how it was resolved"}}
  ],
  "open_risks": [
    {{"vulnerability_id": "V2", "title": "title", "severity": "Critical|High|Medium|Low", "summary": "why it remains open", "recommended_action": "specific next step"}}
  ],
  "plan_strength_score": 7,
  "score_reasoning": "paragraph explaining the 1-10 score — what the plan gets right and where it falls short",
  "recommendations": [
    "specific, actionable recommendation 1",
    "specific, actionable recommendation 2"
  ],
  "overall_assessment": "1-2 paragraph executive summary of the plan's viability after stress-testing"
}}
"""
