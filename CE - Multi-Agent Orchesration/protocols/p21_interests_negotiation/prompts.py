"""Prompt templates for P21: Interests-Based Negotiation protocol."""

SURFACE_INTERESTS_PROMPT = """\
You are {agent_name} participating in an interests-based negotiation exercise.

Your role context: {system_prompt}

**Negotiation Scenario:**
{question}

Your task: Identify your UNDERLYING INTERESTS regarding this scenario — NOT positions \
or demands. Dig deeper than what you want to WHY you want it. Consider:
- What needs must be met?
- What fears or risks concern you?
- What aspirations or opportunities do you see?

Return a JSON object with this exact structure:
```json
{{
  "interests": [
    {{
      "interest": "description of the underlying interest",
      "priority": "high|medium|low",
      "type": "need|fear|aspiration"
    }}
  ]
}}
```

Produce 4-8 distinct interests. Be specific and substantive — generic interests like \
"make money" are not useful. Think about what uniquely matters from your perspective."""

INTEREST_MAP_PROMPT = """\
You are a neutral mediator analyzing interests from multiple stakeholders in a negotiation.

**Negotiation Scenario:**
{question}

**Interests by Stakeholder:**
{interests_block}

Your task: Categorize ALL stated interests into three buckets:
1. **Shared** — Multiple stakeholders share this interest (or very similar ones)
2. **Compatible** — Different interests that do not conflict and can coexist
3. **Conflicting** — Interests that are directly opposed or in tension

For each categorized interest, note which stakeholders hold it.

Return a JSON object with this exact structure:
```json
{{
  "shared": [
    {{"interest": "...", "holders": ["Agent1", "Agent2"], "notes": "..."}}
  ],
  "compatible": [
    {{"interest": "...", "holder": "Agent1", "notes": "..."}}
  ],
  "conflicting": [
    {{
      "interest_a": {{"interest": "...", "holder": "Agent1"}},
      "interest_b": {{"interest": "...", "holder": "Agent2"}},
      "tension": "description of the conflict"
    }}
  ]
}}
```"""

GENERATE_OPTIONS_PROMPT = """\
You are {agent_name} generating creative options for a negotiation.

Your role context: {system_prompt}

**Negotiation Scenario:**
{question}

**Interest Map (categorized interests from all stakeholders):**

Shared interests:
{shared_block}

Compatible interests:
{compatible_block}

Conflicting interests:
{conflicting_block}

Your task: Brainstorm options that satisfy MULTIPLE interests simultaneously. \
Focus on expanding the pie — creating new value — rather than dividing existing value. \
Pay special attention to resolving conflicting interests through creative reframing.

Return a JSON object with this exact structure:
```json
{{
  "options": [
    {{
      "option": "description of the proposed option",
      "satisfies_interests": ["interest1", "interest2"],
      "reasoning": "how this option creates mutual gains"
    }}
  ]
}}
```

Produce 3-6 distinct options. Be specific and actionable."""

SCORE_OPTIONS_PROMPT = """\
You are scoring negotiation options against stakeholder interests.

**Negotiation Scenario:**
{question}

**Options to Evaluate:**
{options_block}

**All Stakeholder Interests:**
{interests_block}

For each option, score how well it satisfies each agent's interests on a 0.0-1.0 scale:
- 1.0 = fully satisfies the agent's key interests
- 0.5 = partially satisfies or is neutral
- 0.0 = actively harms the agent's interests

Return a JSON object with this exact structure:
```json
{{
  "scores": [
    {{
      "option_index": 0,
      "agent_scores": {{
        "AgentName": {{"score": 0.8, "reasoning": "..."}}
      }},
      "pareto_optimal": true
    }}
  ]
}}
```

An option is Pareto-optimal if no agent scores below 0.4 AND no other option makes \
every agent at least as well off with at least one agent strictly better off."""

FINAL_AGREEMENT_PROMPT = """\
You are synthesizing the final agreement for an interests-based negotiation.

**Negotiation Scenario:**
{question}

**Interest Map:**
Shared: {shared_block}
Compatible: {compatible_block}
Conflicting: {conflicting_block}

**Scored Options (with agent satisfaction scores):**
{scored_options_block}

**Pareto-Optimal Options:**
{pareto_block}

Your task: Synthesize the best options into a coherent agreement that maximizes \
mutual gains. If multiple Pareto-optimal options exist, combine compatible elements. \
Address any remaining conflicts with specific trade-offs or phased approaches.

Return a JSON object with this exact structure:
```json
{{
  "agreement": {{
    "summary": "2-3 sentence executive summary of the agreement",
    "key_terms": ["term1", "term2"],
    "interest_satisfaction": {{
      "AgentName": {{"score": 0.85, "satisfied_interests": ["..."], "unsatisfied": ["..."]}}
    }},
    "trade_offs": ["any explicit trade-offs made"],
    "implementation_notes": "how to execute this agreement"
  }}
}}
```"""
