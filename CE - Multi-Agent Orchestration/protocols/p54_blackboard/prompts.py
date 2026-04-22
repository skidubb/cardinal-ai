"""Prompts for P54: Blackboard (Pandemonium)."""

TICK_PROMPT = """You are {agent_name}.

{system_prompt}

A decentralized Blackboard protocol is in progress. You see the full current state of the Blackboard below. Other agents are reading the same state in parallel. There is no orchestrator deciding who speaks or when — it's on you.

QUESTION:
{question}

CURRENT BLACKBOARD STATE (round {tick}/{max_ticks}):

{blackboard_snapshot}

OTHER AGENTS STILL ACTIVE: {active_agents}

YOU HAVE EXACTLY ONE DECISION TO MAKE THIS TICK:

1. CONTRIBUTE — add a new entry to the Blackboard if you have something genuinely useful to add that:
     - covers a topic your specialty owns
     - is NOT already covered by existing entries
     - advances the answer meaningfully
   Emit:
   {{"action":"contribute","topic":"<short-topic-slug e.g. 'financial_risk' or 'technical_feasibility'>","content":"<your contribution, direct prose, 2-6 sentences>","relevance":<0.0-1.0>}}

2. HALT — if the current Blackboard is sufficient from your perspective, or if you have nothing non-redundant to add this tick, emit:
   {{"action":"halt","reason":"<one phrase — e.g. 'nothing to add' or 'financial angle covered'>"}}

Halting is NOT failure. It signals you are satisfied with current state. Protocol terminates when all agents halt (or max ticks hit).

Output exactly one JSON object. No prose outside it."""
