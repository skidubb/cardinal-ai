# Custom Langfuse Evaluators for Coordination Lab

Paste these into Langfuse → Settings → Evaluators → Create New.

For each: set Model to `gemini-3.1-flash-lite-preview` (cheap), Filter to
`Type = GENERATION` + `Metadata generation_type = agent`.

---

## 1. Strategic Depth

**Name:** `Strategic Depth`
**Score range:** 0.0 – 1.0

**Prompt:**

```
You are evaluating the strategic depth of an AI agent's response in a multi-agent orchestration system. The agent was given a strategic question or analytical prompt and produced a response as part of a coordination protocol (e.g., TRIZ failure analysis, Cynefin domain classification, Popper falsification, Klein premortem).

Evaluate the response on strategic depth — does it demonstrate genuine analytical rigor, or is it generic/superficial?

Scoring criteria:
- 0.0-0.2: Generic platitudes, no specific reasoning, could apply to any question
- 0.3-0.4: Some specificity but shallow analysis, missing key considerations
- 0.5-0.6: Adequate analysis with some domain-specific reasoning
- 0.7-0.8: Strong analysis with concrete examples, trade-offs, and non-obvious insights
- 0.9-1.0: Exceptional — identifies second-order effects, challenges assumptions, provides actionable specifics

Input (the prompt given to the agent):
{{input}}

Output (the agent's response):
{{output}}

Respond with JSON: {"reasoning": "...", "score": <float>}
```

---

## 2. Analytical Rigor

**Name:** `Analytical Rigor`
**Score range:** 0.0 – 1.0

**Prompt:**

```
You are evaluating the analytical rigor of an AI agent's response in a strategic decision-making protocol. The agent is one of several (CEO, CFO, CTO, etc.) providing independent analysis that will be synthesized.

Evaluate whether the response demonstrates structured thinking appropriate to the agent's role:
- Does it identify specific risks, trade-offs, or opportunities?
- Does it provide evidence or reasoning for its claims?
- Does it consider multiple scenarios or failure modes?
- Is the analysis role-appropriate (e.g., CFO focuses on financials, CTO on technical feasibility)?

Scoring:
- 0.0-0.2: No structure, just restating the question or giving vague opinions
- 0.3-0.4: Some structure but assertions without backing
- 0.5-0.6: Structured response with basic reasoning
- 0.7-0.8: Well-structured with specific evidence and multi-faceted analysis
- 0.9-1.0: Rigorous framework with quantified risks, concrete scenarios, and clear logic chain

Input:
{{input}}

Output:
{{output}}

Respond with JSON: {"reasoning": "...", "score": <float>}
```

---

## 3. Actionability

**Name:** `Actionability`
**Score range:** 0.0 – 1.0

**Prompt:**

```
You are evaluating whether an AI agent's strategic analysis produces actionable output. In a multi-agent orchestration system, each agent's response should contribute concrete, usable analysis — not just theoretical observations.

Evaluate actionability:
- Does the response identify specific next steps, decisions, or actions?
- Are recommendations concrete enough to act on (who, what, when, how much)?
- Does it distinguish between immediate actions and longer-term considerations?
- Could a decision-maker use this output directly without significant interpretation?

Scoring:
- 0.0-0.2: Pure theory or observation with no actionable content
- 0.3-0.4: Vague recommendations ("consider doing X", "be careful about Y")
- 0.5-0.6: Some specific recommendations but missing details for execution
- 0.7-0.8: Clear, specific recommendations with enough detail to begin execution
- 0.9-1.0: Highly actionable with prioritized steps, success criteria, and contingencies

Input:
{{input}}

Output:
{{output}}

Respond with JSON: {"reasoning": "...", "score": <float>}
```

---

## 4. Role Differentiation

**Name:** `Role Differentiation`
**Score range:** 0.0 – 1.0

**Prompt:**

```
You are evaluating whether an AI agent's response reflects its assigned role/persona in a multi-agent strategic analysis. Each agent (CEO, CFO, CTO, CMO, etc.) should bring a distinct perspective shaped by their domain expertise.

The agent's name and role can be inferred from the observation name (e.g., "llm:CEO - Chief Executive Officer" or "llm:cfo").

Evaluate role differentiation:
- Does the response reflect the agent's domain (finance for CFO, technology for CTO, etc.)?
- Does it use role-appropriate frameworks, metrics, or terminology?
- Does it prioritize concerns relevant to its function?
- Would you be able to guess which agent wrote this based on content alone?

Scoring:
- 0.0-0.2: Completely generic, no role-specific perspective
- 0.3-0.4: Mentions role-relevant topics but analysis is surface-level
- 0.5-0.6: Clear role perspective but could go deeper
- 0.7-0.8: Strong role-specific analysis with domain frameworks and metrics
- 0.9-1.0: Deeply role-embodied — uses specialized terminology, role-specific risk frameworks, and domain-native reasoning

Input:
{{input}}

Output:
{{output}}

Respond with JSON: {"reasoning": "...", "score": <float>}
```

---

## Setup Notes

1. **Disable the 4 default evaluators** (Answer Correctness, Contextcorrectness, Contextrelevance, Helpfulness) — they produce noise for orchestration use cases
2. **Create these 4** with filter: `Type = GENERATION` AND `Metadata generation_type = agent`
3. All use `gemini-3.1-flash-lite-preview` for cost efficiency
4. Scores appear on traces and can be filtered/compared in the Langfuse dashboard
