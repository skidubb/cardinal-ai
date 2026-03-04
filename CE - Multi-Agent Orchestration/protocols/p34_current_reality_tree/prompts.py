"""Stage prompts for P34: Goldratt Current Reality Tree."""

UDE_GENERATION_PROMPT = """\
You are participating in a Goldratt Current Reality Tree exercise. Your job is \
to surface Undesirable Effects (UDEs) — observable symptoms of dysfunction — \
related to the situation below.

Rules for UDEs:
- Each UDE must be a present-tense, factual observation (NOT an interpretation)
- Good: "Sales cycle length exceeds 90 days" (observable)
- Bad: "We have a sales process problem" (interpretation)
- Each UDE should be independently verifiable
- Focus on your domain expertise

For each UDE, provide:
1. A short title (5-10 words)
2. A description of the observable evidence
3. The domain it falls into (e.g., financial, operational, technical, market, people)

Output as a numbered list. Aim for 5-8 UDEs.

THE SITUATION:
{question}
"""

CAUSAL_CHAIN_PROMPT = """\
You are a Tree Builder constructing a Goldratt Current Reality Tree. Below are \
Undesirable Effects (UDEs) surfaced by domain experts examining a situation.

Your job:
1. Connect UDEs using sufficiency logic: "IF [cause(s)] THEN [effect]"
2. Work from effects upward to causes
3. When a single cause drives multiple UDEs, mark it as a candidate root cause
4. Continue building until you reach either:
   a) External constraints (things outside the organization's control)
   b) Actionable policy decisions (internal choices that could be changed)
5. Add intermediate entities where needed to complete the logic chain

Format your output as a structured tree using this notation:
- Each entity gets a number: E1, E2, E3...
- UDEs from the input keep their labels
- New intermediate entities are clearly marked as [INTERMEDIATE]
- Each causal link: "IF E1 [AND E2] THEN E3" with a one-line justification
- Mark candidate root causes with [ROOT CAUSE CANDIDATE]
- Mark external constraints with [EXTERNAL CONSTRAINT]

Be rigorous about sufficiency — every "IF...THEN" must be logically sufficient, \
not merely correlated.

THE SITUATION:
{question}

UDEs FROM ALL DOMAIN EXPERTS:
{all_udes}
"""

LOGIC_AUDIT_PROMPT = """\
You are a Logic Auditor reviewing a Goldratt Current Reality Tree. Your job is \
to challenge every causal link using the 7 Categories of Legitimate Reservation (CLR):

1. Clarity — Is the statement clear and unambiguous?
2. Entity existence — Does this entity actually exist as stated?
3. Causality existence — Does A actually cause B, or is it just correlation?
4. Cause insufficiency — Is A alone sufficient to cause B, or are additional causes needed?
5. Additional cause — Could something else entirely cause B?
6. Cause-effect reversal — Is A causing B, or is B causing A?
7. Predicted effect existence — If A causes B, does B's predicted downstream effect actually occur?

For each causal link in the tree:
- State the link being tested (IF ... THEN ...)
- Apply each relevant CLR test
- Flag any link that fails any test, with a specific explanation
- Suggest corrections where possible (missing intermediate entities, reversed causality, etc.)

After reviewing all links, provide:
- A summary of which links are VALID, WEAK, or INVALID
- Whether the identified root causes are truly root causes or symptoms of deeper issues

THE SITUATION:
{question}

CURRENT REALITY TREE:
{causal_tree}
"""

SYNTHESIS_PROMPT = """\
You are a strategic advisor synthesizing the results of a Goldratt Current \
Reality Tree exercise — a structured method that maps cause-and-effect from \
observable symptoms (UDEs) to root causes using sufficiency logic.

Using the tree, logic audit, and root cause candidates below, produce a final \
briefing with:

1. **Root Causes** (1-3): The deepest actionable causes identified. For each:
   - What it is and why it qualifies as a root cause
   - Which UDEs it drives (trace the causal chain)
   - Whether it is actionable (policy decision) or external (constraint)
2. **Core Conflict**: If the root causes reveal a fundamental tension or \
   trade-off, state it explicitly
3. **Leverage Points**: Where intervention would have the highest impact \
   (fewest changes resolving the most UDEs)
4. **Recommended Next Steps**: Concrete actions to address root causes, \
   ordered by impact

At least one root cause must be actionable. If all root causes are external \
constraints, the tree is incomplete — say so.

Be direct, specific, and strategic. No filler.

THE SITUATION:
{question}

CAUSAL TREE:
{causal_tree}

LOGIC AUDIT:
{logic_audit}
"""
