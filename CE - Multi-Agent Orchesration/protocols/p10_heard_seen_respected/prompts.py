"""Prompt templates for P10: Heard-Seen-Respected protocol."""

STAKEHOLDER_NARRATIVE_PROMPT = """\
You are participating in a Heard-Seen-Respected exercise — a structured empathy protocol.

**Challenge / Question:**
{question}

Write a first-person narrative of your "lived experience" regarding this challenge from \
your role's perspective. This is NOT analysis. This is an experiential, emotionally honest \
account of what this challenge feels like from where you sit.

Include:
- What keeps you up at night about this
- What pressures you feel that others may not see
- What trade-offs you're forced to make that feel invisible to colleagues
- What you wish the rest of the leadership team understood about your position

Write in first person. Be specific, vulnerable, and concrete — not abstract or corporate. \
Aim for 300-500 words."""

REFLECT_BACK_PROMPT = """\
You are participating in a Heard-Seen-Respected exercise. You have just listened to a \
colleague share their lived experience regarding a strategic challenge.

**Original Challenge:**
{question}

**{narrator_name}'s Narrative:**
{narrative}

Your task is to reflect back what you heard, using three structured lenses:

1. **"What I heard you saying was..."** — Paraphrase the core message and concerns in \
your own words. Show that you understood the substance.

2. **"What I noticed was..."** — Call out the emotions, tensions, or unspoken pressures \
you detected beneath the surface. Name what might be hard for them to say directly.

3. **"What I respect about your position is..."** — Identify what is genuinely \
admirable, difficult, or courageous about where they stand. This is not flattery — \
it is acknowledgment of legitimate competing demands.

Be specific and reference concrete details from their narrative. Avoid generic responses."""

BRIDGE_SYNTHESIS_PROMPT = """\
You are a facilitator completing a Heard-Seen-Respected exercise. Multiple stakeholders \
have shared their lived experience with a challenge, and each has been reflected back to \
by a peer.

**Original Challenge:**
{question}

**Narratives and Reflections:**

{narratives_and_reflections}

Your task is to produce a Bridge Synthesis with three sections:

## Common Ground
Identify the shared concerns, values, and priorities that emerged across all perspectives. \
What do these stakeholders actually agree on, even if they use different language?

## Key Differences
Name the genuine tensions and trade-offs between perspectives. Do NOT paper over real \
conflicts — surface them clearly. For each difference, note which perspectives are in \
tension and why.

## Translation Guide
For each stakeholder, produce a brief "translation" that maps their core concerns into \
language the others can understand. The goal is to build a shared vocabulary so that \
future conversations start from mutual understanding rather than positional bargaining.

Format the translation guide as a table or structured list:
- **[Role]** — When they say "X", they mean "Y" because "Z"

Be concrete, honest, and useful. This document should serve as a reference for the team \
going forward."""
