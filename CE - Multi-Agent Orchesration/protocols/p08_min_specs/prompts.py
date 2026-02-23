"""Prompt templates for P08: Min Specs protocol."""

GENERATE_SPECS_PROMPT = """\
You are {agent_name}. {system_prompt}

**Goal / Challenge:**
{question}

Your task: generate a comprehensive list of ALL rules, constraints, specifications, \
and requirements you believe are necessary to achieve this goal successfully.

Think broadly — include operational rules, quality standards, governance constraints, \
resource requirements, process mandates, and any guardrails you consider essential. \
Be specific and concrete. Do not self-censor or pre-filter. We will prune later.

Return your answer as a JSON object with a single key "specs" containing an array of \
objects, each with "id" (S1, S2, ...) and "description" (the spec text).

Example format:
{{"specs": [{{"id": "S1", "description": "All customer data must be encrypted at rest and in transit"}}]}}"""

DEDUP_SPECS_PROMPT = """\
You are a facilitator consolidating specifications from multiple participants.

**Original Goal:**
{question}

**All Submitted Specs:**
{all_specs_block}

Your task:
1. Merge duplicates and near-duplicates into single canonical specs.
2. Combine overlapping specs where one subsumes another.
3. Preserve distinct specs even if they seem minor — do NOT eliminate yet.
4. Re-number the consolidated list starting from S1.

Return a JSON object with a single key "specs" containing an array of objects, \
each with "id" (S1, S2, ...) and "description" (the consolidated spec text).

{{"specs": [{{"id": "S1", "description": "..."}}]}}"""

ELIMINATION_TEST_PROMPT = """\
You are evaluating whether a specific rule is truly essential.

**Goal:**
{question}

**Spec under review:**
{spec_id}: {spec_description}

**Critical question:** If this spec were REMOVED entirely, would it be impossible \
to achieve the stated goal? Would removing it guarantee failure, or could you still \
succeed without it?

Think carefully. Many specs are "nice to have" or "best practice" but not truly \
minimum requirements. A minimum spec is one whose absence makes the purpose impossible.

Return a JSON object:
{{"spec_id": "{spec_id}", "verdict": "MUST_HAVE" or "REMOVABLE" or "BORDERLINE", "reasoning": "brief explanation"}}"""

BORDERLINE_VOTE_PROMPT = """\
You are {agent_name}. {system_prompt}

**Goal:**
{question}

The following spec has been flagged as borderline — it is unclear whether it is \
truly a minimum requirement or can be safely removed.

**Spec:** {spec_id}: {spec_description}

**Context — specs already confirmed as must-haves:**
{must_have_block}

Given the must-haves above, do we ALSO need this borderline spec? Or would the \
must-haves alone be sufficient to achieve the goal without it?

Vote KEEP or REMOVE with a one-sentence rationale.

Return a JSON object:
{{"spec_id": "{spec_id}", "vote": "KEEP" or "REMOVE", "rationale": "..."}}"""

FINAL_SYNTHESIS_PROMPT = """\
You are producing the final Min Specs output for the following goal.

**Goal:**
{question}

The team started with {total_specs} candidate specifications and has systematically \
tested each one. Here is the outcome:

**Must-Have Specs (passed elimination test):**
{must_have_block}

**Eliminated Specs (removing them does not make the goal impossible):**
{eliminated_block}

**Borderline Specs resolved by vote:**
{borderline_block}

Your task:
1. Produce the definitive minimum specification set — the smallest set of rules \
that, if followed, makes success possible, and if any single one is removed, \
makes success impossible.
2. For each spec, provide a clear rationale for why it is indispensable.
3. Note any important trade-offs or risks created by what was eliminated.
4. Provide guidance on how to use this minimum spec set in practice.

Structure your response as:
- **Executive Summary** (2-3 sentences on the min spec philosophy for this goal)
- **Minimum Specifications** (numbered, each with rationale)
- **What We Eliminated and Why** (brief, for transparency)
- **Risks and Trade-offs** (what you lose by going minimal)
- **Implementation Guidance** (how to apply these specs)"""
