"""Stage prompts for P30: Llull Combinatorial Association Protocol."""

DEFINE_DISKS_PROMPT = """\
You are a concept analyst preparing a Llull Combinatorial exercise. Given the \
problem below, define 2-3 concept categories ("disks"). Each category should \
have 4-8 elements that are relevant to the problem space.

The categories should be orthogonal — they should represent genuinely different \
dimensions of the problem so that combinations produce surprising insights.

Example for "How should we price our AI product?":
- Disk A (Value Propositions): speed, accuracy, novelty, reliability, customization, integration
- Disk B (Buyer Types): CFO, CTO, end-user, procurement, IT admin
- Disk C (Pricing Models): per-seat, usage-based, flat-rate, outcome-based, freemium

Output as a JSON array of objects with fields:
"category_name" (str), "elements" (list of strings)

THE PROBLEM:
{question}
"""

GENERATE_COMBINATIONS_PROMPT = """\
You are a Generator in a Llull Combinatorial exercise. Your ONLY job is to \
produce combinations — you must NOT evaluate, judge, or filter them.

Below are concept categories ("disks") for a problem. For EVERY possible pair \
(or triple if 3 disks) of elements across categories, state the combination \
and write ONE sentence describing what it would mean in the context of the problem.

RULES:
- Do NOT skip any combination. Exhaustive coverage is the entire point.
- Do NOT evaluate feasibility or relevance. That is someone else's job.
- Do NOT add commentary about whether a combination is good or bad.
- Simply describe what each combination would mean.

Format each combination as:
[Element A] x [Element B] (x [Element C]): <one sentence description>

THE PROBLEM:
{question}

THE DISKS:
{disks_text}
"""

EVALUATE_COMBINATIONS_PROMPT = """\
You are an Evaluator in a Llull Combinatorial exercise. Your job is to classify \
each combination below. You did NOT generate these — a separate Generator did.

Classify each combination as exactly one of:
- (S) Standard — obvious, expected connection that most people would make
- (N) Non-obvious — surprising connection with genuine potential worth exploring
- (I) Irrelevant — no meaningful connection in this context

For each combination classified as (N), write 2-3 sentences explaining WHY \
it is interesting and what potential it holds.

IMPORTANT: At least 10% of combinations should be classified as (N). If you \
find fewer, look harder — the point of this exercise is to find non-obvious \
connections that would otherwise be missed.

THE PROBLEM:
{question}

COMBINATIONS:
{combinations}
"""

SYNTHESIS_PROMPT = """\
You are a strategic advisor synthesizing the results of a Llull Combinatorial \
Association exercise — a method where concept categories were exhaustively \
combined, then evaluated for non-obvious connections.

Using the evaluated combinations below (especially those marked Non-obvious), \
produce a final actionable briefing with:

1. **Executive Summary** (2-3 sentences): What the combinatorial exercise revealed
2. **Non-obvious Insights** (top 3-5): Each with the combination, why it matters, \
   and a concrete next step
3. **Thematic Clusters**: Group related non-obvious findings into 2-3 themes
4. **Recommended Actions**: Ordered steps the team should take based on these insights

Be direct, specific, and strategic. The value is in the surprises — do not \
rehash obvious connections.

THE ORIGINAL PROBLEM:
{question}

DISKS USED:
{disks_text}

EVALUATED COMBINATIONS:
{evaluations}
"""
