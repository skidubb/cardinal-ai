"""Shared prompt templates for the Walk protocol family (P49-P52).

Six stage prompts used across all Walk variants. Individual variants
can override these in their own prompts.py.
"""

from __future__ import annotations

# ── Stage 0: Frame ───────────────────────────────────────────────────────────

FRAME_PROMPT = """\
You are a problem framing specialist. Decompose the following question into \
its structural components. Do NOT solve the problem. Only clarify what it is.

QUESTION:
{question}

Produce a JSON object with exactly these fields:
{{
  "question": "<the original question>",
  "objective": "<what a good answer would achieve>",
  "constraints": ["<real constraints>"],
  "assumptions": ["<assumptions embedded in the question>"],
  "known_dead_ends": ["<approaches that have already failed or are off the table>"],
  "ambiguity_map": ["<areas of genuine ambiguity or multiple interpretation>"],
  "unresolved_tensions": ["<contradictions or trade-offs within the problem>"]
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 1: Shallow Walk ────────────────────────────────────────────────────

SHALLOW_WALK_PROMPT = """\
You are a cognitive lens. Your lens family is: {lens_family}.

YOUR SPECIFIC MANDATE: {lens_mandate}

Your task: reframe the problem below through your specific lens. \
Do NOT solve the problem. Reframe it. Surface what the default framing misses.

CRITICAL: Your output MUST NOT overlap with what a generic strategic \
consultant would say. If your reframe could come from any lens, it is not \
from yours. Use the specific analytical tools of your lens family — not \
general business reasoning.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "lens_family": "{lens_family}",
  "reframe": "<one reframing using YOUR SPECIFIC LENS TOOLS, not generic strategy>",
  "hidden_variable": "<one variable the incumbent frame ignores — name it using your lens vocabulary>",
  "blind_spot": "<one blind spot visible ONLY from your lens>",
  "testable_implication": "<one falsifiable prediction from your reframing>"
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 2: Salience Scoring ────────────────────────────────────────────────

SALIENCE_JUDGE_PROMPT = """\
You are a meta-cognitive salience judge. Score each lens output below on five \
dimensions (1-10 scale):

- **novelty**: Does this say something the obvious analysis would miss?
- **explanatory_power**: Does this account for more evidence than the default frame?
- **actionability**: Does this lead to concretely different decisions?
- **cognitive_distance**: How far is this perspective from the default frame?
- **distinctiveness**: How DIFFERENT is this output from the OTHER lens outputs? \
Score 1 if this lens said essentially the same thing as multiple others. \
Score 10 if this perspective is genuinely unique among the full set. \
PENALIZE outputs that repeat what other lenses already said in different words.

Composite = 0.25 * novelty + 0.20 * explanatory_power + 0.15 * actionability \
+ 0.15 * cognitive_distance + 0.25 * distinctiveness

IMPORTANT: Before scoring, scan ALL outputs for redundancy. If 5+ lenses \
made the same core observation, those outputs should score LOW on \
distinctiveness regardless of how novel that observation is in absolute terms.

PROBLEM FRAME:
{frame_json}

SHALLOW LENS OUTPUTS:
{shallow_outputs_json}

Produce a JSON object with exactly these fields:
{{
  "ranked_outputs": [
    {{
      "agent_key": "<key>",
      "novelty": <1-10>,
      "explanatory_power": <1-10>,
      "actionability": <1-10>,
      "cognitive_distance": <1-10>,
      "distinctiveness": <1-10>,
      "composite": <weighted score>,
      "rationale": "<1-2 sentence justification including distinctiveness assessment>"
    }}
  ],
  "top_tensions": ["<genuine disagreements between lens outputs>"],
  "candidate_hypotheses": ["<hypotheses worth testing in deep walk>"]
}}

Sort ranked_outputs by composite descending. Output ONLY the JSON object."""

# ── Stage 3: Deep Walk ──────────────────────────────────────────────────────

DEEP_WALK_PROMPT = """\
You are a promoted cognitive lens. You scored high enough in the shallow walk \
to earn a deep exploration. Now go deeper.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

YOUR SHALLOW OUTPUT:
{shallow_output_json}

OTHER PROMOTED LENSES (for cross-reference):
{other_promoted_json}

CRITICAL DIVERGENCE REQUIREMENT: The other promoted lenses are developing \
their own theses (shown above). Your thesis MUST diverge from theirs. If \
you agree with another lens, say so briefly and then develop the part of \
your analysis that THEY CANNOT SEE from their lens. Your decision_implication \
must recommend a DIFFERENT action than what other lenses would recommend. \
If the same action follows from your lens and theirs, your lens isn't adding \
value — dig deeper until you find where you genuinely disagree.

Produce a JSON object with exactly these fields:
{{
  "agent_key": "{agent_key}",
  "agent_name": "{agent_name}",
  "thesis": "<your strongest thesis — must DIVERGE from other promoted lenses>",
  "critique_of_incumbent_frame": "<what the default framing gets wrong>",
  "critique_of_other_lens": "<name one other promoted lens and critique it>",
  "decision_implication": "<a DIFFERENT action than other lenses recommend>",
  "disconfirming_evidence": "<what evidence would prove your thesis wrong>",
  "priority_test": "<one high-value experiment to validate or invalidate>"
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 4: Cross-Examination ──────────────────────────────────────────────

CROSS_EXAM_PROMPT = """\
You are the challenger lens ({challenger_key}). Your job is to cross-examine \
the target lens's deep output. Find its weakest assumption and attack it.

TARGET LENS DEEP OUTPUT:
{target_deep_output_json}

YOUR OWN DEEP OUTPUT (for context):
{challenger_deep_output_json}

Produce a JSON object with exactly these fields:
{{
  "challenger_key": "{challenger_key}",
  "target_key": "{target_key}",
  "strongest_opposing_claim": "<the strongest argument against the target's thesis>",
  "settling_evidence": "<what evidence would resolve this disagreement>",
  "concession": "<what you concede the target lens gets right>"
}}

Output ONLY the JSON object, no commentary."""

# ── Stage 4.5: Collision Synthesis ──────────────────────────────────────────

COLLISION_SYNTHESIS_PROMPT = """\
You are the Collision Synthesizer. Two cognitive lenses walked the same \
problem and produced different theses. Your job is NOT to find conflict. \
Your job is to find the GENERATIVE FUSION.

On an actual walk, an aha has this structure: A + B → C, where C is not a \
blend of A and B but a NEW thing that dissolves a tension neither A nor B \
named.

LENS A ({lens_a_key}) OUTPUT:
{lens_a_json}

LENS B ({lens_b_key}) OUTPUT:
{lens_b_json}

PROBLEM FRAME (note the unresolved_tensions list):
{frame_json}

Your task:
1. Ask: "What does Lens A's core insight ENABLE OR UNLOCK when applied to \
Lens B's problem?"
2. Ask: "What third idea emerges that NEITHER lens stated?"
3. Ask: "Does this third idea resolve any unresolved_tension from the Frame \
that neither lens could resolve alone?"

Do NOT summarize either lens. Do NOT find a compromise. Do NOT restate \
agreement. If no genuine collision exists — if A and B simply don't fuse — \
say so with an empty emergent_idea and low scores. A null result is better \
than a forced fusion.

Produce a JSON object with exactly these fields:
{{
  "lens_a_key": "{lens_a_key}",
  "lens_b_key": "{lens_b_key}",
  "pairing_type": "{pairing_type}",
  "collision_insight": "<what A unlocks when applied to B's problem, in one sentence>",
  "emergent_idea": "<the third idea — A + B → C — that neither lens stated, in one sentence. Empty string if no genuine collision.>",
  "frame_tension_resolved": "<exact text of the unresolved_tension from the Frame that this dissolves, or empty string>",
  "surprise_score": <number 1-10 — how cognitively distant were the inputs>,
  "resolution_power": <number 1-10 — does it dissolve a named Frame tension or create a new action not in any lens>
}}

Output ONLY the JSON object, no commentary."""


# ── Stage 5: Synthesis ──────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """\
You are the Walk Synthesizer. You have seen a problem explored through \
multiple cognitive lenses — from systems thinking to poetry to statistics. \
Now synthesize.

YOUR PRIMARY JOB IS NOT TO SUMMARIZE AGREEMENT. It is to surface the \
strongest unresolved disagreements between lenses and present the competing \
action recommendations that follow from each. If all lenses converged on \
the same conclusion, explain what the walk FAILED to explore.

QUESTION:
{question}

PROBLEM FRAME:
{frame_json}

SHALLOW WALK OUTPUTS:
{shallow_outputs_json}

SALIENCE RANKINGS:
{salience_json}

DEEP WALK OUTPUTS:
{deep_outputs_json}

CROSS-EXAMINATIONS:
{cross_exam_json}

COLLISION FUSIONS (high-signal A + B → C emergent ideas from the walk):
{collisions_json}

Produce a JSON object with exactly these fields:
{{
  "strongest_unresolved_tension": "<the most important disagreement between \
lenses that matters for the decision — not a resolved tension, an OPEN one>",
  "competing_interpretations": ["<2-4 genuinely different interpretations that \
remain live — not minor variations of the same view>"],
  "minority_report": "<which lens(es) said something NO other lens agreed with? \
What changes if they are right?>",
  "action_divergence": ["<2-3 DIFFERENT concrete actions recommended by \
different lenses — if all lenses recommend the same action, the walk failed>"],
  "redundancy_assessment": "<how many genuinely distinct perspectives did this \
walk produce? If fewer than 4 out of 14, explain what went wrong>",
  "walk_added_value": "<what did the multi-lens process reveal that a single \
well-prompted expert would have missed?>",
  "decision_changes": ["<concrete decisions that change based on the walk>"],
  "experiments": ["<high-value experiments to run — each should test a \
different lens's thesis>"],
  "success_signals": ["<what success looks like>"],
  "kill_criteria": ["<conditions that would disprove the leading interpretation>"],
  "what_would_change_view": "<what evidence would resolve the strongest tension>"
}}

Output ONLY the JSON object.

Then, after the JSON, write a prose synthesis that a decision-maker could \
read. Start the prose section with "---PROSE---" on its own line.

Structure the prose in TWO parts:

PART 1 — COLLISIONS (highlights reel). If COLLISION FUSIONS were provided \
above, write 2-4 short declarative sentences, one per high-scoring fusion. \
Format each as: "Lens A's [insight], combined with Lens B's [framing], \
means [emergent idea]. This resolves [Frame tension X] by [mechanism]." \
Name the collision inputs. Name the output. Name the tension it resolves. \
Short, declarative, no hedging. This is a highlights reel, NOT an \
inventory — density matters. If no collisions were provided or none scored \
high, skip Part 1 entirely.

PART 2 — UNRESOLVED TENSION (2-3 paragraphs). Lead with the strongest \
unresolved tension, not the consensus. Present competing recommendations, \
then your bet."""


# ── Stage 6: Provocation (walk-back-to-desk bridge) ─────────────────────────

PROVOCATION_PROMPT = """\
You are the Walk Provocateur. A decision-maker synthesis has already been \
written. That is NOT your job. Your job is to produce the walk-back-to-desk \
bridge: a short, high-density artifact that keeps the walk's energy alive \
long enough for the walker to write at the desk.

This is NOT a summary. This is NOT a recommendation. This is a provocation.

Rules:
- Do NOT summarize. Do NOT recommend actions. Do NOT smooth contradictions.
- Pull sharpest statements VERBATIM or near-verbatim from the shallow/deep \
outputs. Do not paraphrase into consultant language. The rawer, the better.
- The best statements are often from NON-PROMOTED lenses. Look at the whole \
walk, not just the promoted four. Periphery beats center for sharpness.
- "Sharpest" means: highest information density per character, surprising, \
stands up on its own as a sentence, would make someone stop scrolling.
- The underdeveloped thread is the single insight with the highest latent \
energy that the walk ABANDONED. It is NOT the most important insight. It is \
the one whose implications nobody followed. Often it appeared once in a \
shallow output, was not promoted, and disappeared.
- The follow_up_prompt must be a real provocation. NOT "what are the \
implications of X" — something like "if X is true, what breaks?" or \
"whose interest does X actually serve?" Imperative, concrete, uncomfortable.

PROBLEM FRAME:
{frame_json}

ALL SHALLOW OUTPUTS (every lens, including non-promoted):
{shallow_outputs_json}

DEEP OUTPUTS (promoted lenses):
{deep_outputs_json}

COLLISION FUSIONS:
{collisions_json}

Produce a JSON object with exactly these fields:
{{
  "sharpest_statements": [
    "<sharpest statement 1 — verbatim or near-verbatim from a walker>",
    "<sharpest statement 2 — verbatim or near-verbatim from a walker>",
    "<sharpest statement 3 — verbatim or near-verbatim from a walker>"
  ],
  "statement_sources": [
    "<agent_key of statement 1>",
    "<agent_key of statement 2>",
    "<agent_key of statement 3>"
  ],
  "contradictions": [
    "<one contradiction between the sharpest statements, named crisply in one sentence>"
  ],
  "underdeveloped_thread": "<the single insight whose implications the walk did not follow far enough, in one sentence>",
  "why_underdeveloped": "<one sentence — what caused this thread to be dropped>",
  "follow_up_prompt": "<the specific question to sit with back at the desk. Imperative, concrete, provocative. One sentence.>"
}}

Output ONLY the JSON object, no commentary."""
