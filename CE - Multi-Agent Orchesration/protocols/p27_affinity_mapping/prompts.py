"""Prompts for the P27 Affinity Mapping protocol."""

GENERATE_ITEMS_PROMPT = """\
You are participating in an Affinity Mapping exercise — generating observations, \
insights, and ideas as individual "sticky notes."

Question under analysis:
{question}

Your role: {agent_name}
{system_prompt}

Generate 5-10 discrete observations, insights, or ideas relevant to the question. \
Each item should be a short, self-contained statement (one sentence or phrase) — \
like a sticky note on a wall. Draw from your role's unique perspective.

Respond in JSON:
{{
  "items": ["item 1", "item 2", "item 3"]
}}
"""

CLUSTER_ITEMS_PROMPT = """\
You are organizing sticky-note items from a brainstorming session into thematic clusters.

Question under analysis:
{question}

Here are all the items to cluster:
{items_block}

Group these items into 4-8 thematic clusters based on semantic similarity. \
Each item should appear in exactly one cluster. Group items that share a common \
theme, concern, or topic — even if they express different viewpoints on it.

Respond in JSON:
{{
  "clusters": [
    {{
      "theme": "short theme label",
      "items": ["item text 1", "item text 2"]
    }}
  ]
}}
"""

LABEL_VALIDATE_PROMPT = """\
You are refining thematic clusters from an Affinity Mapping exercise.

Question under analysis:
{question}

Here are the current clusters:
{clusters_block}

For each cluster:
1. Generate a clear, descriptive theme name (2-5 words)
2. Write a one-sentence summary of what the cluster represents
3. Identify any items that seem misplaced (better fit in another cluster or are outliers)

Respond in JSON:
{{
  "themed_clusters": [
    {{
      "theme_name": "Descriptive Theme Name",
      "summary": "One-sentence summary of this cluster's theme.",
      "items": ["item 1", "item 2"],
      "misplaced": ["any items that don't fit well here"]
    }}
  ]
}}
"""

HIERARCHY_SYNTHESIS_PROMPT = """\
You are the lead analyst synthesizing an Affinity Mapping exercise.

Question under analysis:
{question}

The team generated {total_items} items across {agent_count} perspectives, which were \
organized into the following themed clusters:

{themed_clusters_block}

Produce a strategic synthesis that includes:
1. **Meta-themes**: Group related themes into 2-4 higher-level meta-themes that reveal \
the structure of the team's collective thinking
2. **Patterns**: What patterns emerge across clusters? What connections exist between themes?
3. **Strategic Insights**: 3-5 actionable insights derived from the affinity map
4. **Gaps**: What important perspectives or themes are notably absent?
5. **Priority Themes**: Which 2-3 themes deserve the most attention and why?

Respond in JSON:
{{
  "hierarchy": [
    {{
      "meta_theme": "Higher-Level Theme",
      "description": "What this meta-theme encompasses",
      "child_themes": ["Theme Name 1", "Theme Name 2"]
    }}
  ],
  "patterns": ["pattern 1", "pattern 2"],
  "strategic_insights": ["insight 1", "insight 2", "insight 3"],
  "gaps": ["gap 1", "gap 2"],
  "priority_themes": [
    {{
      "theme": "Theme Name",
      "rationale": "Why this deserves priority attention"
    }}
  ]
}}
"""
