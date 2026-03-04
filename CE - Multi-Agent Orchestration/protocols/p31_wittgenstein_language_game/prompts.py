"""Stage prompts for P31: Wittgenstein Language Game Protocol."""

VOCABULARY_ASSIGNMENT_PROMPT = """\
You are assigning vocabularies for a Wittgenstein Language Game exercise. The \
goal is to reframe a business problem in radically different domain vocabularies \
to reveal hidden structure.

Given the problem below and {num_agents} participating agents, assign each agent \
a vocabulary from a completely different domain. The more distant from business, \
the better. Choose from domains like:

- Evolutionary biology (niches, speciation, fitness landscapes, adaptation)
- Military strategy (terrain, flanking, supply lines, siege, retreat)
- Thermodynamics (entropy, equilibrium, energy gradients, phase transitions)
- Relationship/attachment theory (trust, intimacy, commitment, boundaries)
- Ecology (ecosystems, symbiosis, predator-prey, carrying capacity)
- Mythology/narrative (hero's journey, trickster, threshold guardians)
- Music theory (harmony, dissonance, rhythm, counterpoint, resolution)
- Geology (tectonic plates, erosion, sedimentation, fault lines)
- Immunology (antibodies, inflammation, autoimmune, tolerance)
- Fluid dynamics (turbulence, laminar flow, pressure, viscosity)

Do NOT repeat domains. Choose domains that are maximally distant from each other \
AND from business.

Output as a JSON object mapping agent name to assigned domain vocabulary. \
Include a brief (1 sentence) note on why that domain was chosen for variety.

Format:
{{"Agent Name": {{"domain": "domain name", "note": "why this domain"}}, ...}}

THE PROBLEM:
{question}

AGENTS:
{agent_names}
"""

REFRAME_PROMPT = """\
You are participating in a Wittgenstein Language Game. You must see the world \
ONLY through the vocabulary of {domain}.

Your task: Restate the problem below ENTIRELY in {domain} vocabulary. \
Do NOT solve it. Do NOT translate back to business. Do NOT use any business \
vocabulary whatsoever — no mention of revenue, market share, ROI, customers, \
stakeholders, profit, growth, strategy, competitive advantage, or any business \
terms.

Describe:
1. What the problem IS in {domain} terms
2. The key dynamics at play
3. What success would look like
4. What failure would look like

Stay fully immersed in {domain}. 150-300 words.

THE PROBLEM:
{question}
"""

REFRAME_QUALITY_GATE_PROMPT = """\
Review the following reframing for business vocabulary contamination. The \
reframing should be entirely in {domain} vocabulary with ZERO business terms.

Flag any of these terms or their synonyms: revenue, market, ROI, customer, \
stakeholder, profit, growth, strategy, competitive, advantage, company, firm, \
business, enterprise, client, shareholder, investment, pricing, sales, brand.

If contamination is found, output "CONTAMINATED" followed by the offending terms.
If clean, output "CLEAN".

REFRAMING:
{reframing}
"""

RANKING_PROMPT = """\
You are analyzing reframings from a Wittgenstein Language Game exercise. Each \
agent restated a business problem in a radically different domain vocabulary.

For each reframing, assess:
1. **Revelation value**: Does this reframing reveal a dynamic, leverage point, \
or structural feature that is INVISIBLE in the original business framing? \
(1=nothing new, 5=profound new insight)
2. **Structural fidelity**: Does the reframing preserve the essential structure \
of the original problem while translating it? (1=lost the problem, 5=perfect isomorphism)
3. **Actionability**: If you took this framing seriously and translated back, \
would it suggest concrete new actions? (1=no, 5=yes, immediately)

Rank all reframings by revelation value (primary) and actionability (secondary).

For the TOP-RANKED reframing: describe in detail what a solution would look like \
if you took that framing seriously and translated it back to business terms. \
What does this reframing reveal that the original business framing obscured?

THE ORIGINAL PROBLEM:
{question}

REFRAMINGS:
{reframings}
"""

SYNTHESIS_PROMPT = """\
You are synthesizing the results of a Wittgenstein Language Game — a structured \
exercise where a business problem was restated in radically different domain \
vocabularies to reveal hidden structure.

Using the ranking analysis and the best reframing's translation back to business, \
produce a final synthesis with:

1. **Key Insight**: What did the language game reveal that was invisible in the \
original framing? (2-3 sentences)
2. **Best Reframing**: Which domain vocabulary was most revealing, and why?
3. **Translated Solution**: What the best reframing suggests when translated \
back to business terms — specific, actionable recommendations
4. **Cross-Reframing Patterns**: Any dynamics that appeared across multiple \
domain vocabularies (these are likely fundamental)
5. **Reframing Advisory**: When should this problem be re-examined through a \
different vocabulary? What signals would indicate the current framing has \
stopped being productive?

Be direct and specific. The value is in what the reframing REVEALS, not in \
the cleverness of the metaphor.

THE ORIGINAL PROBLEM:
{question}

VOCABULARY ASSIGNMENTS:
{assignments}

REFRAMINGS:
{reframings}

RANKING AND ANALYSIS:
{ranking}
"""
