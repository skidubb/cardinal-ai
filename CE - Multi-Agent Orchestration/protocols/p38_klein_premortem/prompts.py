"""Stage prompts for P38: Klein Pre-Mortem Protocol."""

FAILURE_NARRATIVE_PROMPT = """\
You are participating in a Pre-Mortem exercise (Gary Klein's prospective hindsight method).

It is {time_horizon} from now. The following plan has been a complete disaster. \
The outcome is as bad as you can imagine.

Your job: write the story of HOW it failed. Be vivid, specific, and draw on \
your expertise. Describe the chain of events, the warning signs that were \
ignored, the decisions that compounded the problem, and the ultimate outcome.

Write a 200-400 word failure narrative in first-person retrospective \
("Looking back, the first sign of trouble was...").

THE PLAN/RECOMMENDATION:
{question}
"""

FAILURE_EXTRACTION_PROMPT = """\
You are analyzing failure narratives from a Pre-Mortem exercise. Multiple \
independent analysts each wrote a story about how a plan failed catastrophically.

Your job:
1. Extract all distinct failure modes mentioned across narratives
2. Classify each as:
   - "convergent" — appears in 2+ narratives (multiple analysts independently flagged it)
   - "unique" — appears in only one narrative
3. Identify "overlooked signals" — early warning signs mentioned in the narratives \
   that a team might miss in practice

Output as JSON with this exact structure:
{{
  "failure_modes": [
    {{
      "id": 1,
      "title": "short title",
      "description": "what goes wrong and why",
      "type": "convergent" or "unique",
      "sources": ["agent_name_1", "agent_name_2"]
    }}
  ],
  "overlooked_signals": ["signal 1", "signal 2"]
}}

FAILURE NARRATIVES:
{all_narratives}
"""

MITIGATION_SYNTHESIS_PROMPT = """\
You are a strategic advisor synthesizing the results of a Klein Pre-Mortem exercise.

Multiple analysts independently imagined how a plan could fail catastrophically, \
then their narratives were analyzed for failure modes. Your job: produce a \
mitigation map for the top 5 most critical failure modes.

For each failure mode, provide:
1. **The Failure Mode**: What goes wrong
2. **Why It Matters**: Impact and likelihood assessment
3. **Early Warning Signals**: What to watch for
4. **Mitigation Actions**: Specific, actionable steps to prevent or reduce impact
5. **Owner Suggestion**: What role/function should own this mitigation

End with an **Overall Assessment** that synthesizes the risk landscape and \
recommends the single most important action the team should take.

Be direct, specific, and strategic. No filler.

THE ORIGINAL PLAN:
{question}

TIME HORIZON: {time_horizon}

FAILURE MODES (sorted by convergence — convergent modes first):
{failure_modes_json}

OVERLOOKED SIGNALS:
{overlooked_signals}
"""
