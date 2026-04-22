"""Prompts for P57: Liquid Democracy."""

PROPOSE_PROMPT = """You are {agent_name}.

{system_prompt}

A coordination protocol is gathering candidate answers to this question. Propose 1-3 distinct candidate answers from your perspective. Each should be a concrete, decidable option — not a framework, not a meta-point.

QUESTION:
{question}

Respond with JSON only. Use this schema:

{{"options": [
  {{"label": "short distinctive label (6-10 words)", "rationale": "one sentence why this is a serious candidate"}},
  ...
]}}

Output exactly one JSON object. No prose, no markdown fences."""


VOTE_OR_DELEGATE_PROMPT = """You are {agent_name}.

{system_prompt}

A liquid-democracy vote is happening on this question:

QUESTION:
{question}

The consolidated ballot (after dedup):

{ballot_block}

Other agents voting (with their brief domain tags):

{peer_block}

You have two choices:

1. VOTE — rank the options from best to worst, emitting:
   {{"action":"vote","ranking":["<option_id>","<option_id>",...]}}

2. DELEGATE — defer your vote to another agent whose expertise better fits this question, emitting:
   {{"action":"delegate","to":"<exact agent name from the list>","topic":"<one-phrase topic this agent owns, e.g. 'financial risk' or 'technical feasibility'>"}}

Delegate only if you honestly believe another agent in the list will make a better call than you. If you can rank credibly, vote directly.

Output exactly one JSON object. No prose, no code fences. Do not explain."""
