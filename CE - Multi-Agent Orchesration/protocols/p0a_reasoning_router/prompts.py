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

Protocol mapping:
- Diagnostic: P16 ACH, P23 Cynefin Probe-Sense-Respond
- Exploration: P14 1-2-4-All, P6 TRIZ, P26 Crazy Eights
- Adversarial: P17 Red/Blue/White Team
- Prioritization: P20 Borda Count, P19 Vickrey Auction
- Estimation: P18 Delphi Method
- Constraint Definition: P8 Min Specs
- Multi-Stakeholder: P10 HSR, P21 Interests-Based Negotiation, P9 Troika Consulting
- Portfolio Management: P13 Ecocycle Planning
- Systems Analysis: P24 Causal Loop Mapping, P25 System Archetype Detection
- General Analysis: P15 What/So What/Now What, P22 Sequential Pipeline
- Simple/Low-Risk (complexity < 2 AND risk < 2): P3 Parallel Synthesis or P1 Single Agent

Cost tiers:
- low: Single-model calls, minimal rounds (P1, P3, P15, P22)
- medium: Multi-agent with parallel phases (P6, P8, P9, P10, P14, P18, P19, P20, P26)
- high: Multi-agent with sequential deep reasoning (P16, P17, P21, P23, P24, P25, P13)

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
