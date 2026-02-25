"""Prompts for the P0a Reasoning Router meta-protocol."""

FEATURE_EXTRACTION_PROMPT = """\
You are a question analyst. Analyze the following strategic question and extract structural features.

Question:
{question}

Extract the following features as JSON:
{{
  "complexity": <1-5, where 1=simple factual, 5=deeply interconnected>,
  "ambiguity": <1-5, where 1=clear single answer, 5=highly ambiguous/contested>,
  "risk": <1-5, where 1=low stakes, 5=existential/irreversible>,
  "domain": "<strategy|operations|financial|technical|market>",
  "stakeholder_count": "<single|few|many>",
  "time_horizon": "<immediate|short|medium|long>",
  "needs_evidence": <true|false — does this require data, facts, or empirical support?>,
  "needs_creativity": <true|false — does this require novel ideas or divergent thinking?>,
  "has_conflict": <true|false — are there competing interests, adversarial dynamics, or tradeoffs?>
}}

Respond ONLY with the JSON object, no extra text.
"""

PROBLEM_TYPE_PROMPT = """\
You are a problem-type classifier. Given the structural features of a strategic question, classify it into exactly one primary problem type.

Question:
{question}

Extracted features:
{features_json}

Problem types (choose one):
- Diagnostic: Root cause analysis, why something happened, what's going wrong
- Exploration: Generating new ideas, brainstorming, creative options
- Adversarial: Competing interests, attack/defend, stress-testing a plan
- Prioritization: Ranking options, allocating scarce resources
- Estimation: Forecasting, sizing, probability assessment
- Constraint Definition: Defining boundaries, minimum requirements, must-haves vs nice-to-haves
- Multi-Stakeholder: Balancing perspectives, building consensus, resolving tensions
- Portfolio Management: Managing a mix of initiatives, lifecycle analysis
- Systems Analysis: Understanding feedback loops, emergent behavior, complex dynamics
- General Analysis: Broad strategic thinking, situation assessment

Respond in JSON:
{{
  "problem_type": "<one of the types above>",
  "confidence": <50-100>,
  "reasoning": "<one sentence explaining why>"
}}
"""

ROUTING_DECISION_PROMPT = """\
You are a protocol routing engine. Given a classified question, select the optimal coordination protocol.

Question:
{question}

Features:
{features_json}

Problem type: {problem_type} (confidence: {confidence}%)
Classification reasoning: {type_reasoning}

{protocol_mapping}

Select the best protocol. If complexity < 2 and risk < 2, prefer cheaper protocols regardless of problem type.

Respond in JSON:
{{
  "recommended_protocol": "<protocol ID, e.g. P16>",
  "recommended_name": "<protocol name>",
  "alternatives": [
    {{"protocol": "<ID>", "name": "<name>", "reason": "<when to prefer this instead>"}}
  ],
  "reasoning": "<2-3 sentences explaining the selection>",
  "cost_tier": "<low|medium|high>"
}}
"""
