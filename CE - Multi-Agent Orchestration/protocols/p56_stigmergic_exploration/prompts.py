"""Prompts for P56: Stigmergic Exploration."""

SEED_PROMPT = """You are {agent_name}.

{system_prompt}

A stigmergic exploration is beginning on this question:

QUESTION:
{question}

This is the SEED round. You will propose {k} distinct candidate paths (strategies, approaches, or directions) to explore. Each path should be:
- A concrete, specific direction — not a meta-observation
- Different enough from the others to actually cover different ground

After all agents seed their paths, subsequent rounds will reinforce, refine, or explore new paths based on where the collective attention converges. Think of these as possible hypotheses or strategies.

Respond with JSON only:

{{"paths": [
  {{"description": "1-2 sentences per path"}},
  ...
]}}

No code fences, no prose outside the JSON."""


TICK_PROMPT = """You are {agent_name}.

{system_prompt}

A stigmergic exploration is in round {tick}/{max_ticks}. Paths with more pheromone have been reinforced by you and your peers in prior rounds; pheromone decays by {decay_rate:.0%} each round, so only paths that keep getting reinforced dominate.

QUESTION:
{question}

CURRENT PHEROMONE MAP (sorted by strength):

{pheromone_map}

YOU HAVE EXACTLY ONE DECISION TO MAKE THIS TICK:

1. REINFORCE — pick an existing path (by path_id) and add a specific refinement or supporting argument. Boosts its pheromone. Emit:
   {{"action":"reinforce","path_id":"<exact path_id>","refinement":"<your refinement, 1-3 sentences>"}}

2. EXPLORE — propose a new, distinct path the group hasn't considered yet. Emit:
   {{"action":"explore","description":"<1-2 sentences describing the new path>"}}

3. HALT — if current convergence is sufficient from your perspective and you have nothing to add, emit:
   {{"action":"halt","reason":"<one phrase>"}}

Bias your attention toward high-pheromone paths (they're where the group is converging), but exploring is valuable when you see a gap. Halting is NOT failure — it's a signal you're satisfied.

Output exactly one JSON object. No prose outside it."""
