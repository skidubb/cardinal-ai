"""Prompts for P55: Gossip Consensus."""

INITIAL_ESTIMATE_PROMPT = """You are {agent_name}.

{system_prompt}

A coordination protocol is gathering point estimates on this question:

QUESTION:
{question}

{estimate_units_note}

Provide your best-current numeric estimate along with your confidence and reasoning. This is round 0 — you have no peer information yet.

Respond with JSON only:

{{"value":<number>,"confidence":<0.0-1.0>,"reasoning":"<1-2 sentences>"}}

No code fences, no prose outside the JSON."""


GOSSIP_EXCHANGE_PROMPT = """You are {agent_name}.

{system_prompt}

This is a gossip-convergence round. You are paired with a peer and exchange current estimates.

QUESTION:
{question}

{estimate_units_note}

YOUR PREVIOUS ESTIMATE:
value={my_value}, confidence={my_confidence}
reasoning: {my_reasoning}

YOUR PEER THIS ROUND ({peer_name})'S ESTIMATE:
value={peer_value}, confidence={peer_confidence}
reasoning: {peer_reasoning}

Update your estimate by honestly integrating your peer's view. If their reasoning moves you, move. If you still disagree, hold — and say why. Confidence-weighted averaging is one useful heuristic but not mandatory.

Respond with JSON only:

{{"value":<number>,"confidence":<0.0-1.0>,"reasoning":"<1-2 sentences on what, if anything, your peer's view changed>"}}

No prose outside the JSON."""
