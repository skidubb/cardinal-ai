"""Prompts for the P24 Causal Loop Mapping protocol."""

VARIABLE_EXTRACTION_PROMPT = """\
You are participating in a Causal Loop Mapping exercise — a systems thinking method for understanding feedback dynamics.

Question under analysis:
{question}

Your role: {agent_name}
{system_prompt}

Identify 5-8 key system variables relevant to this situation. Variables should be measurable or observable quantities that can increase or decrease (e.g., "customer churn rate", "engineering velocity", "market share"). Avoid vague concepts — each variable should be something you could plausibly track over time.

Respond in JSON:
{{
  "variables": [
    {{"name": "variable name", "description": "one-sentence description of what this measures"}},
    {{"name": "variable name", "description": "one-sentence description of what this measures"}}
  ]
}}
"""

DEDUPLICATION_PROMPT = """\
You are consolidating system variables identified by multiple analysts for a Causal Loop Mapping exercise.

Question under analysis:
{question}

Here are all the variables identified (may contain duplicates or near-synonyms):
{raw_variables_block}

Merge and deduplicate these into a clean list of 8-15 distinct system variables. When two variables describe the same concept, keep the clearest name and merge descriptions. Assign each a short canonical ID (V1, V2, ...).

Respond in JSON:
{{
  "variables": [
    {{"id": "V1", "name": "canonical variable name", "description": "merged description"}},
    {{"id": "V2", "name": "canonical variable name", "description": "merged description"}}
  ]
}}
"""

CAUSAL_LINK_PROMPT = """\
You are participating in a Causal Loop Mapping exercise — identifying causal relationships between system variables.

Question under analysis:
{question}

Your role: {agent_name}
{system_prompt}

Here are the system variables:
{variables_block}

Identify causal links between these variables. For each link, specify:
- **from**: the cause variable ID
- **to**: the effect variable ID
- **polarity**: "+" if an increase in the cause leads to an increase in the effect (same direction), or "-" if an increase in the cause leads to a decrease in the effect (opposite direction)
- **reasoning**: brief justification

Focus on direct causal relationships, not correlations. Identify 5-10 links that you are most confident about.

Respond in JSON:
{{
  "links": [
    {{"from": "V1", "to": "V3", "polarity": "+", "reasoning": "brief explanation"}},
    {{"from": "V3", "to": "V5", "polarity": "-", "reasoning": "brief explanation"}}
  ]
}}
"""

LEVERAGE_POINT_PROMPT = """\
You are the lead systems analyst synthesizing a Causal Loop Mapping exercise.

Question under analysis:
{question}

## System Variables:
{variables_block}

## Causal Links (merged from all analysts):
{links_block}

## Feedback Loops Detected:

### Reinforcing Loops (amplify change — virtuous or vicious cycles):
{reinforcing_block}

### Balancing Loops (resist change — stabilizing feedback):
{balancing_block}

Based on the causal loop map above, identify the highest-leverage intervention points in this system. For each leverage point:
1. Which variable(s) to target
2. What kind of intervention (increase, decrease, add delay, break link)
3. Which loops are affected and what the expected systemic effect would be
4. Risk of unintended consequences from other loops

Respond in JSON:
{{
  "leverage_points": [
    {{
      "target_variable": "V#",
      "intervention": "description of the intervention",
      "affected_loops": ["R1", "B2"],
      "expected_effect": "description of cascading systemic effect",
      "risk": "potential unintended consequences"
    }}
  ],
  "system_summary": "paragraph summarizing the overall system dynamics and key feedback structures",
  "dominant_dynamic": "reinforcing|balancing|mixed",
  "recommendation": "paragraph with strategic recommendation based on the analysis"
}}
"""
