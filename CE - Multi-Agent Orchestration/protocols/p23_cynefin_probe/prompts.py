"""Prompts for the P23 Cynefin Probe-Sense-Respond protocol."""

DOMAIN_CLASSIFICATION_PROMPT = """\
You are participating in a Cynefin framework classification exercise.

Question / situation under analysis:
{question}

Your role: {agent_name}
{system_prompt}

Classify this situation into ONE of the five Cynefin domains:

- **Clear** (formerly "Obvious"): Cause-and-effect is obvious to everyone. Best practices exist. Sense-Categorize-Respond.
- **Complicated**: Cause-and-effect requires expert analysis. Good practices exist but need expertise to identify. Sense-Analyze-Respond.
- **Complex**: Cause-and-effect is only apparent in retrospect. No right answers — emergent patterns. Must probe with safe-to-fail experiments first. Probe-Sense-Respond.
- **Chaotic**: No discernible cause-and-effect. Crisis mode. Must act immediately to stabilize, then sense. Act-Sense-Respond.
- **Confused** (formerly "Disorder"): It is unclear which domain applies. The situation must be broken down into sub-problems.

Consider: How predictable are the outcomes? How much agreement exists on the approach? Are there established best practices, or is this novel territory?

Respond in JSON:
{{
  "domain": "clear|complicated|complex|chaotic|confused",
  "reasoning": "2-3 sentence justification for your classification",
  "confidence": 75
}}
"""

# Domain-specific response prompts ----------------------------------------

CLEAR_RESPONSE_PROMPT = """\
The team has classified the following situation as **Clear** (obvious cause-and-effect, best practices apply).

Question / situation:
{question}

Your role: {agent_name}
{system_prompt}

Apply the "Sense-Categorize-Respond" approach:
1. Identify the category this situation falls into
2. State the established best practice
3. Recommend the straightforward response

Be concise and direct — this is a solved problem.

Respond in JSON:
{{
  "category": "what category this falls into",
  "best_practice": "the established best practice to apply",
  "recommended_action": "specific action to take",
  "rationale": "brief rationale"
}}
"""

COMPLICATED_RESPONSE_PROMPT = """\
The team has classified the following situation as **Complicated** (requires expert analysis, good practices exist).

Question / situation:
{question}

Your role: {agent_name}
{system_prompt}

Apply the "Sense-Analyze-Respond" approach:
1. What expert analysis is needed?
2. What are the key factors to evaluate?
3. What good practice applies given your analysis?
4. What is your recommended course of action?

Provide substantive expert analysis from your domain perspective.

Respond in JSON:
{{
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "analysis": "your expert analysis of the situation",
  "good_practice": "the good practice that applies",
  "recommended_action": "specific recommended action",
  "caveats": "important caveats or conditions"
}}
"""

COMPLEX_RESPONSE_PROMPT = """\
The team has classified the following situation as **Complex** (emergent, unpredictable — must probe first).

Question / situation:
{question}

Your role: {agent_name}
{system_prompt}

Apply the "Probe-Sense-Respond" approach. Design 1-2 safe-to-fail experiments:
- Each probe should be cheap and fast to run
- It should generate signal about what works, even if it fails
- Define what "success" and "failure" look like for each probe
- Explain what you would learn from each outcome

This is the CORE of the Cynefin framework — we cannot analyze our way to an answer, we must experiment.

Respond in JSON:
{{
  "probes": [
    {{
      "name": "short name for the experiment",
      "description": "what to do",
      "success_signal": "what success looks like",
      "failure_signal": "what failure looks like",
      "learning_outcome": "what we learn either way",
      "cost_and_timeline": "rough cost/time to run"
    }}
  ],
  "emergent_patterns": "any patterns you suspect but cannot yet confirm",
  "dampening_actions": "what to stop doing that may be making things worse"
}}
"""

CHAOTIC_RESPONSE_PROMPT = """\
The team has classified the following situation as **Chaotic** (no clear cause-and-effect, crisis mode).

Question / situation:
{question}

Your role: {agent_name}
{system_prompt}

Apply the "Act-Sense-Respond" approach:
1. What IMMEDIATE stabilizing action should be taken? (Act first, analyze later)
2. What signals should we watch for after acting?
3. What is the next move once we have stabilized?

Speed matters more than perfection. The goal is to move from Chaotic to Complex.

Respond in JSON:
{{
  "immediate_action": "the single most important thing to do RIGHT NOW",
  "stabilization_steps": ["step 1", "step 2", "step 3"],
  "signals_to_watch": ["signal 1", "signal 2"],
  "transition_plan": "how to move from crisis mode to a more manageable state"
}}
"""

CONFUSED_RESPONSE_PROMPT = """\
The team has classified the following situation as **Confused** (unclear which Cynefin domain applies).

Question / situation:
{question}

Your role: {agent_name}
{system_prompt}

When in the Confused domain, the first step is to DECOMPOSE the situation into sub-problems that can each be classified independently.

Break down this situation into 2-4 distinct sub-problems. For each, suggest which Cynefin domain it likely belongs to.

Respond in JSON:
{{
  "sub_problems": [
    {{
      "name": "short name",
      "description": "what this sub-problem is about",
      "likely_domain": "clear|complicated|complex|chaotic",
      "reasoning": "why this domain"
    }}
  ],
  "meta_observation": "what makes this situation hard to classify as a whole"
}}
"""

SYNTHESIS_PROMPT = """\
You are synthesizing a Cynefin framework analysis for the following situation.

Question / situation:
{question}

## Domain Classification
The team classified this situation as: **{consensus_domain}**
Was the classification contested? {was_contested}

### Individual Classifications:
{domain_votes_block}

## Domain-Appropriate Responses
{responses_block}

Produce a unified action plan that:
1. Acknowledges the domain classification and what it implies
2. Synthesizes the team's domain-appropriate responses into a coherent plan
3. Identifies the most important next steps
4. Notes risks and what would cause a re-classification to a different domain

Respond in JSON:
{{
  "domain_summary": "one paragraph explaining why this domain was selected and what it means",
  "action_plan": "detailed, synthesized action plan drawing from all agent responses",
  "priority_actions": ["action 1", "action 2", "action 3"],
  "risks": ["risk 1", "risk 2"],
  "reclassification_triggers": ["trigger 1", "trigger 2"],
  "confidence_note": "how confident the team should be in this classification and plan"
}}
"""
