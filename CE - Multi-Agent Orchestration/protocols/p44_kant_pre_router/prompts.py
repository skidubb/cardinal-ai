"""Prompts for P44: Kant Architectonic Pre-Router."""

CLASSIFICATION_PROMPT = """\
You are a question classifier. Classify the following question on TWO axes.

AXIS 1 — PROBLEM TYPE (pick exactly one):
- Diagnostic: Understanding what is happening or why
- Exploration: Mapping possibilities, options, or landscapes
- Strategic: Making a high-stakes decision with trade-offs
- Paradox: Navigating tensions, contradictions, or wicked problems
- Forecasting: Predicting outcomes or future states
- Operational: Improving execution, processes, or efficiency

AXIS 2 — MODALITY (pick exactly one):
- ASSERTORIC ("what IS"): Questions about current state, requiring evidence, data, observation. Route to data-heavy protocols.
- PROBLEMATIC ("what COULD be"): Questions about possibility, options, alternatives. Route to divergent/creative protocols.
- APODICTIC ("what MUST be"): Questions about necessity, constraints, non-negotiables. Route to constraint analysis / logical protocols.

Based on the classification, recommend the best protocol from this list:
- P3 Parallel Synthesis: Good default for straightforward questions needing multiple perspectives
- P4 Multi-Round Debate: Best for strategic decisions with genuine trade-offs
- P5 Constraint Negotiation: Best for questions with competing constraints or non-negotiables
- P6 TRIZ Inversion: Best for stress-testing plans or identifying failure modes
- P7 Wicked Questions: Best for paradoxes and tensions that cannot be resolved
- P8 Min Specs: Best for identifying the minimum viable set of constraints
- P9 Troika Consulting: Best for getting peer consulting on a specific challenge
- P14 1-2-4-All: Best for building consensus from individual to group
- P16 ACH: Best for diagnostic questions requiring hypothesis evaluation
- P17 Red/Blue/White: Best for adversarial analysis of strategies
- P18 Delphi Method: Best for forecasting with iterative expert convergence
- P22 Sequential Pipeline: Best for operational questions requiring staged processing
- P24 Causal Loop Mapping: Best for understanding systemic dynamics and feedback loops

Output a JSON object with these fields:
- "problem_type": one of Diagnostic, Exploration, Strategic, Paradox, Forecasting, Operational
- "modality": one of ASSERTORIC, PROBLEMATIC, APODICTIC
- "modality_reasoning": 1-2 sentences explaining the modality classification
- "recommended_protocol": the protocol identifier (e.g., "P4 Multi-Round Debate")
- "routing_rationale": 1-2 sentences explaining the protocol recommendation

THE QUESTION:
{question}
"""
