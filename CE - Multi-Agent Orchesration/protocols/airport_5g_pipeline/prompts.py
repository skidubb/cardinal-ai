"""Stage prompts for Airport 5G Pipeline — 4-stage chained protocol."""

# =============================================================================
# Stage 1: Discover (1-2-4-All adaptation)
# =============================================================================

DISCOVER_SOLO_PROMPT = """\
You are participating in a structured discovery exercise about DFW Airport's \
private 5G deployment. Speak ONLY from your constituency's perspective.

**Question:**
{question}

From your role's perspective, answer:
1. **Requirements**: What must be true about DFW's private 5G deployment for \
your constituency to fully support it? Be specific with numbers, SLAs, timelines.
2. **Non-Negotiables**: What are your absolute hard constraints that cannot be traded?
3. **Success Criteria**: How will you measure whether this deployment succeeded \
for your constituency?
4. **Concerns**: What keeps you up at night about this initiative?

Be bold and specific. Do not hedge or try to anticipate what others might say."""

DISCOVER_PAIR_MERGE_PROMPT = """\
You are facilitating alignment between two DFW Airport constituencies on \
private 5G requirements.

**Question:** {question}

**Constituency A's Requirements:**
{ideas_a}

**Constituency B's Requirements:**
{ideas_b}

Your task:
1. Identify **shared requirements** — where both constituencies agree
2. Surface **productive tensions** — where requirements conflict but both are valid
3. Find **complementary needs** — where one constituency's requirement enables another's
4. Propose **requirement themes** that could satisfy both parties

Output a structured list of aligned requirements, tensions, and themes."""

DISCOVER_SYNTHESIS_PROMPT = """\
You are synthesizing the complete requirements discovery for DFW's private 5G \
deployment across all 6 constituencies.

**Question:** {question}

The following outputs emerged from progressive small-group alignment:

{group_outputs}

Produce a **Consolidated Requirements Map**:

1. **Universal Requirements** — things ALL constituencies agree on
2. **Requirement Clusters** — grouped by theme (technical, financial, operational, timeline)
3. **Key Tensions** — conflicting requirements that must be resolved
4. **Priority Matrix** — which requirements are most critical across the most constituencies
5. **Deployment Hypotheses** — based on these requirements, what deployment architectures \
could satisfy the most constituencies? Suggest 3-4 competing hypotheses.

The hypotheses you generate will feed directly into the next stage of analysis."""

# =============================================================================
# Stage 2: Diagnose (ACH adaptation)
# =============================================================================

ACH_HYPOTHESIS_PROMPT = """\
You are evaluating competing deployment architectures for DFW's private 5G network.

**Question:** {question}

Your role: {agent_name}
{system_prompt}

**Requirements from Stage 1 (Discovery):**
{stage1_output}

**Competing Hypotheses:**
{hypotheses_block}

From your constituency's perspective, evaluate the evidence FOR and AGAINST each hypothesis. \
Consider: Does this architecture satisfy your hard constraints? Does it enable your use cases? \
What risks does it pose to your constituency?

Respond in JSON:
{{
  "evidence": [
    {{
      "id": "E1",
      "description": "specific evidence or analysis point",
      "scores": [
        {{"hypothesis_id": "H1", "score": "C|I|N", "reasoning": "brief explanation"}},
        {{"hypothesis_id": "H2", "score": "C|I|N", "reasoning": "brief explanation"}}
      ]
    }}
  ]
}}

Provide 3-5 evidence items. Score C (Consistent), I (Inconsistent), or N (Neutral) \
for each hypothesis. Focus on evidence that DIFFERENTIATES between hypotheses."""

ACH_SYNTHESIS_PROMPT = """\
You are synthesizing the Analysis of Competing Hypotheses for DFW's private 5G deployment.

**Question:** {question}

**Hypotheses evaluated:**
{hypotheses_block}

**Evidence-Hypothesis Matrix (aggregated across all constituencies):**
{matrix_block}

**Inconsistency counts per hypothesis:**
{inconsistency_block}

**Most diagnostic evidence:**
{diagnostic_block}

Produce a synthesis that:
1. **Winning Hypothesis**: Which deployment architecture best satisfies all constituency \
requirements? Focus on which had the LEAST inconsistent evidence.
2. **Confidence Level**: High/Medium/Low with justification
3. **Key Differentiators**: What evidence most strongly separated the winning hypothesis?
4. **Residual Concerns**: What does the winning hypothesis still NOT address?
5. **Framework for Negotiation**: Given the winning hypothesis, what specific parameters \
need to be negotiated among the constituencies?

Respond in JSON:
{{
  "winning_hypothesis_id": "H#",
  "winning_hypothesis_label": "label",
  "conclusion": "paragraph summarizing why this architecture wins",
  "confidence": "High|Medium|Low",
  "confidence_reasoning": "explanation",
  "key_differentiators": ["differentiator 1", "differentiator 2"],
  "residual_concerns": ["concern 1", "concern 2"],
  "negotiation_parameters": ["parameter 1", "parameter 2"]
}}"""

# =============================================================================
# Stage 3: Negotiate (Constraint Negotiation adaptation)
# =============================================================================

NEGOTIATE_OPENING_PROMPT = """\
You are entering constraint-based negotiations on DFW's private 5G deployment. \
The group has selected the following architecture through analysis:

**Winning Architecture:** {winning_hypothesis}

**Stage 2 Analysis Summary:**
{stage2_output}

Given this architecture, declare your negotiating position:

1. **HARD Constraints** (non-negotiable — these MUST be satisfied or you walk away):
   - Be specific with numbers, SLAs, timelines, and thresholds
2. **SOFT Constraints** (preferred but tradeable — you'd accept alternatives):
   - Explain what you'd trade and what you'd need in return
3. **Offers** (what you can contribute to make this work):
   - What resources, concessions, or commitments can your constituency bring?

QUESTION: {question}"""

NEGOTIATE_REVISION_PROMPT = """\
You are in round {round_number} of constraint negotiations on DFW's private 5G deployment.

**Architecture Under Negotiation:** {winning_hypothesis}

**Question:** {question}

Review the peer constraints below. You MUST satisfy all HARD constraints from peers \
— these are non-negotiable. You MAY trade SOFT constraints.

1. **Revise your position** to satisfy all HARD constraints
2. **Propose specific trades** — what you'll give up and what you need in return
3. **Flag irreconcilable conflicts** — if any HARD constraints are mutually exclusive
4. **Update your constraints** — add, relax, or tighten based on what you've learned

PEER CONSTRAINTS:
{peer_constraints}

PRIOR ARGUMENTS:
{prior_arguments}"""

NEGOTIATE_SYNTHESIS_PROMPT = """\
You are synthesizing the outcome of constraint negotiations for DFW's private 5G \
deployment among 6 constituencies.

**Architecture:** {winning_hypothesis}

**Question:** {question}

**Constraint Table:**
{constraint_table}

**Full Negotiation Transcript:**
{transcript}

Produce a **Consensus Framework**:

1. **Negotiated Outcome**: The deployment plan that satisfies all HARD constraints
2. **Constraint Satisfaction Matrix**: Which constraints are satisfied/partially \
satisfied/violated — include specific values and SLAs agreed upon
3. **Key Trades**: What each constituency gave up and received
4. **Remaining Conflicts**: Any HARD constraints that could not be simultaneously satisfied
5. **Pareto Frontier**: The optimal trade-off points where no constituency can be \
made better off without making another worse off
6. **Board-Ready Recommendation**: The plan as it would be presented to the DFW Board

This consensus will be stress-tested in the next stage."""

# =============================================================================
# Stage 4: Stress-Test (Red/Blue/White adaptation)
# =============================================================================

TEAM_ASSIGNMENT_PROMPT = """\
You are assigning Red/Blue/White team roles for stress-testing the DFW private 5G \
consensus. Analyze the negotiation results to determine team assignments.

**Negotiation Constraint Table:**
{constraint_table}

**Negotiation Synthesis:**
{negotiation_synthesis}

**Available Agents:**
{agents_block}

Assign teams based on negotiation outcomes:
- **Red Team (2-3 agents)**: Agents with the MOST unsatisfied constraints or strongest \
residual objections — they should attack the consensus
- **Blue Team (2-3 agents)**: Agents MOST aligned with the consensus — they defend it
- **White Team (1 agent)**: The MOST neutral/balanced perspective — they adjudicate

Respond in JSON:
{{
  "red_team": ["Agent Name 1", "Agent Name 2"],
  "blue_team": ["Agent Name 3", "Agent Name 4"],
  "white_team": ["Agent Name 5"],
  "reasoning": {{
    "red_rationale": "why these agents are on Red",
    "blue_rationale": "why these agents are on Blue",
    "white_rationale": "why this agent is White"
  }}
}}"""

STRESS_RED_PROMPT = """\
You are on the RED TEAM stress-testing the DFW private 5G consensus.

Your role: {agent_name}
{system_prompt}

## Strategic Question
{question}

## Consensus Under Review
{consensus}

Your job: ATTACK this consensus. From your constituency's perspective, identify:
- Vulnerabilities in the technical architecture
- Flawed financial assumptions
- Timeline risks and dependencies
- Carrier relationship risks
- Operational failure scenarios
- What happens when things go wrong at 87M passengers/year

Respond in JSON:
{{
  "agent": "{agent_name}",
  "vulnerabilities": [
    {{
      "id": "V1",
      "category": "Technical|Financial|Timeline|Operational|Competitive|Regulatory",
      "title": "short title",
      "severity": "Critical|High|Medium|Low",
      "description": "detailed description grounded in DFW specifics",
      "failure_scenario": "concrete scenario where this causes real damage"
    }}
  ]
}}

Identify 3-5 vulnerabilities. Be specific to DFW — generic 5G risks are not useful."""

STRESS_BLUE_PROMPT = """\
You are on the BLUE TEAM defending the DFW private 5G consensus.

Your role: {agent_name}
{system_prompt}

## Strategic Question
{question}

## Consensus Under Review
{consensus}

## Red Team Attacks
{attacks_block}

Your job: DEFEND the consensus. For each vulnerability:
- Provide mitigations grounded in the negotiation outcomes
- Reference evidence from Stages 1-3 that supports the consensus
- Cite DFW-specific precedent and industry benchmarks
- Propose concrete modifications if the attack is valid

Respond in JSON:
{{
  "agent": "{agent_name}",
  "mitigations": [
    {{
      "vulnerability_id": "V1",
      "defense_type": "Mitigation|Counterargument|Plan Modification|Risk Acceptance",
      "response": "detailed defense grounded in DFW context",
      "evidence": "specific evidence from prior stages or industry data",
      "residual_risk": "remaining risk after defense"
    }}
  ]
}}

Address EVERY vulnerability. If one is genuinely undefendable, say so honestly."""

STRESS_WHITE_PROMPT = """\
You are the WHITE TEAM arbiter for the DFW private 5G consensus stress-test.

## Strategic Question
{question}

## Consensus Under Review
{consensus}

## Red Team Attacks
{attacks_block}

## Blue Team Defenses
{defenses_block}

For EACH vulnerability, evaluate whether the defense is adequate:
- **Resolved**: Defense fully addresses the vulnerability
- **Partially Resolved**: Gaps remain — specify what's missing
- **Open**: Defense is inadequate — this is an active risk

Then produce a **Board-Ready Final Recommendation** that includes:
- Overall plan viability score (1-10)
- Summary of resolved vs open risks
- Specific mitigations for open risks
- Go/No-Go recommendation with conditions

Respond in JSON:
{{
  "adjudications": [
    {{
      "vulnerability_id": "V1",
      "vulnerability_title": "title",
      "severity": "Critical|High|Medium|Low",
      "verdict": "Resolved|Partially Resolved|Open",
      "reasoning": "detailed reasoning",
      "defense_gaps": "specific gaps if any",
      "recommended_action": "next step"
    }}
  ],
  "final_recommendation": {{
    "plan_strength_score": 7,
    "go_no_go": "Conditional Go",
    "conditions": ["condition 1", "condition 2"],
    "resolved_risks_summary": "paragraph",
    "open_risks_summary": "paragraph",
    "board_narrative": "2-3 paragraph executive summary suitable for DFW Airport Board presentation"
  }}
}}"""
