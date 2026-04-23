"""Prompts for P01 Single Agent.

The agent's own system prompt (from Agent Builder's _ROLE_PROMPTS) handles
role-specific behavior. P01 is a thin protocol wrapper.

Classifier prompt below is used ONLY when the caller passes no agent and
auto-selection is enabled — it scores the 56-agent roster against the
question and returns the single best fit.
"""

CLASSIFIER_PROMPT = """You route a question to the single best agent from a roster.

QUESTION:
{question}

ROSTER (agent_key — role description):
{roster_block}

Pick exactly ONE agent whose role best matches what the question is actually asking for. Consider:
- The specialty signaled by the question (finance → cfo, pipeline → sales, architecture → cto, etc.)
- Tool access the answer will need (web search, financial data, code, etc.)
- Whose perspective would produce the most useful single-agent answer

Respond with JSON only, no prose or code fences:

{{"agent_key":"<one exact key from the roster>","fit_score":<0.0-1.0>,"reason":"<one sentence, ~20 words>"}}

fit_score meaning:
  1.0  perfect match — the role exists for exactly this kind of question
  0.8  strong match — clear primary specialty, slight mismatch on scope
  0.6  acceptable match — role can handle it but isn't purpose-built
  0.4  weak match — no great fit in roster; this is closest-available
  <0.4 no roster agent fits well

Output the JSON object only."""
