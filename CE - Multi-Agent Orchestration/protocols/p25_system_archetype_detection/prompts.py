"""Prompts for the P25 System Archetype Detection protocol."""

DYNAMICS_OBSERVATION_PROMPT = """\
You are {agent_name}. {system_prompt}

Analyze the following situation and identify the key dynamic patterns you observe — \
recurring behaviors, feedback effects, unintended consequences, and systemic trends.

Situation:
{question}

For each dynamic pattern you observe, describe:
- What is happening (the observable behavior)
- How it changes over time (growing, declining, oscillating, stuck)
- What seems to drive it

Respond in JSON:
{{
  "dynamics": [
    {{
      "pattern": "<short name for the pattern>",
      "description": "<2-3 sentences describing the dynamic>"
    }}
  ]
}}
"""

DYNAMICS_MERGE_PROMPT = """\
You are a systems analyst. Given multiple experts' observations of dynamic patterns in a situation, \
deduplicate and consolidate them into a canonical list.

Situation:
{question}

Raw observations from all experts:
{raw_dynamics_block}

Merge similar patterns, remove duplicates, and produce a clean canonical list. \
Assign each a short ID (D1, D2, ...).

Respond in JSON:
{{
  "dynamics": [
    {{
      "id": "D1",
      "pattern": "<short name>",
      "description": "<consolidated description>"
    }}
  ]
}}
"""

ARCHETYPE_MATCHING_PROMPT = """\
You are {agent_name}. {system_prompt}

Given the observed dynamics in a situation, score how well each of the 8 standard system \
archetypes fits. For each archetype, provide a fit score (0-100) and brief reasoning.

Situation:
{question}

Observed dynamics:
{dynamics_block}

The 8 system archetypes:

1. **Fixes That Fail** — A quick fix addresses a symptom but creates side effects that \
worsen the original problem over time.
   Structure: Problem → Quick Fix → Symptom Relief + Unintended Consequence → Worse Problem

2. **Shifting the Burden** — A symptomatic solution is used instead of a fundamental one. \
The symptomatic solution undermines the capacity for the fundamental solution.
   Structure: Problem → Symptomatic Solution (easy) + Fundamental Solution (hard) → \
Dependency on symptomatic solution grows

3. **Limits to Growth** — A reinforcing process of growth hits a balancing constraint \
that slows or reverses it.
   Structure: Growth Engine → Success → Hits Limit → Slowdown/Reversal

4. **Eroding Goals** — A gap between goal and reality leads to lowering the goal rather \
than improving performance.
   Structure: Gap → Pressure → Lower Goal (instead of improve) → New lower gap → Repeat

5. **Escalation** — Two parties each respond to the other's actions with increasingly \
aggressive moves, creating a reinforcing spiral.
   Structure: Party A acts → Party B responds stronger → Party A responds stronger → Spiral

6. **Success to the Successful** — Initial advantage leads to more resources being \
allocated, compounding the advantage while starving alternatives.
   Structure: A succeeds → A gets more resources → A succeeds more → B gets less → B fails

7. **Tragedy of the Commons** — Individually rational behavior depletes a shared resource, \
harming everyone.
   Structure: Individual gains → Shared resource depletes → Everyone loses

8. **Growth and Underinvestment** — Growth strains capacity, but investment in capacity \
is delayed until performance degrades and demand drops.
   Structure: Growth → Strain → Delay investment → Performance drops → Demand drops

Score each archetype's fit to the observed dynamics.

Respond in JSON:
{{
  "scores": [
    {{
      "archetype": "<archetype name>",
      "score": <0-100>,
      "reasoning": "<1-2 sentences explaining the fit or lack thereof>"
    }}
  ]
}}
"""

SYNTHESIS_PROMPT = """\
You are a senior systems thinking analyst. Given a situation, its observed dynamics, and \
multiple experts' archetype matching scores, produce the final analysis.

Situation:
{question}

Observed dynamics:
{dynamics_block}

Aggregated archetype scores (averaged across experts):
{scores_block}

For the top-matching archetype(s) (score >= 50), provide:
1. A structural mapping: which elements of the situation correspond to which archetype components
2. Archetype-specific intervention recommendations

Respond in JSON:
{{
  "best_matches": [
    {{
      "archetype": "<name>",
      "score": <average score>,
      "structural_mapping": {{
        "<archetype component>": "<situation element>"
      }},
      "reasoning": "<2-3 sentences on why this archetype fits>"
    }}
  ],
  "interventions": [
    {{
      "archetype": "<which archetype this addresses>",
      "intervention": "<specific recommended action>",
      "leverage_point": "<where in the system to intervene>",
      "rationale": "<why this intervention works for this archetype>"
    }}
  ]
}}
"""
