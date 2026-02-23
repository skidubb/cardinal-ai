"""Prompts for the P0b Skip Gate meta-protocol."""

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
  "time_horizon": "<immediate|short|medium|long>"
}}

Respond ONLY with the JSON object, no extra text.
"""

GATE_DECISION_PROMPT = """\
You are a cost-aware routing gate. Given the structural features of a strategic question, \
decide whether the question can be adequately answered by a single agent ("skip") or requires \
a full multi-agent coordination protocol ("escalate").

Question:
{question}

Extracted features:
{features_json}

Decision rules:
- If complexity < 2 AND risk < 2 AND ambiguity < 2 → SKIP (single agent is sufficient)
- If any dimension >= 4 → ESCALATE (multi-agent needed for rigor)
- Otherwise → use your judgment based on the overall profile

If escalating, recommend the best protocol family:
- Diagnostic → P16 ACH
- Exploration → P14 1-2-4-All
- Adversarial → P17 Red/Blue/White
- Prioritization → P20 Borda Count
- Estimation → P18 Delphi Method
- Systems Analysis → P24 Causal Loop Mapping
- General → P3 Parallel Synthesis

Respond in JSON:
{{
  "decision": "<skip|escalate>",
  "confidence": <50-100>,
  "reasoning": "<2-3 sentences explaining the decision>",
  "estimated_cost_savings": "<high|medium|low — how much compute is saved by skipping>",
  "recommended_protocol": "<protocol ID if escalating, null if skipping>",
  "recommended_name": "<protocol name if escalating, null if skipping>"
}}
"""

SINGLE_AGENT_PROMPT = """\
You are a senior strategic advisor. Answer the following question directly and thoroughly.

Question:
{question}

Provide a clear, well-structured response covering key considerations, risks, and recommendations.
"""
