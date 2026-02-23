# P27: Affinity Mapping

**Category:** Design Thinking
**Agents:** Any collection (default: CEO, CFO, CTO, CMO)

## Overview

Affinity Mapping is a collaborative sense-making protocol where multiple agents generate discrete observations and ideas ("sticky notes"), which are then semantically clustered into themes, validated, and organized into a strategic hierarchy.

## Protocol Phases

| Phase | Model | Description |
|-------|-------|-------------|
| 1. Generate Items | Opus (parallel) | Each agent produces 5-10 sticky-note items from their perspective |
| 2. Pool & Cluster | Haiku | All items are pooled and grouped into 4-8 thematic clusters via LLM-based semantic clustering |
| 3. Label & Validate | Haiku | Each cluster gets a descriptive theme name, summary, and misplaced-item check |
| 4. Hierarchy & Synthesis | Opus | Meta-themes, cross-cluster patterns, strategic insights, gaps, and priority themes |

## Usage

```bash
# Default (4 agents)
python -m protocols.p27_affinity_mapping.run -q "What are the key challenges in scaling our platform internationally?"

# All 7 agents
python -m protocols.p27_affinity_mapping.run -q "..." -a ceo cfo cto cmo coo cpo cro

# JSON output
python -m protocols.p27_affinity_mapping.run -q "..." --json
```

## Output Structure

```json
{
  "question": "...",
  "raw_items": {"CEO": ["item1", ...], "CFO": [...]},
  "total_items": 42,
  "clusters": [{"theme": "...", "items": [...]}],
  "themed_clusters": [{"theme_name": "...", "summary": "...", "items": [...], "misplaced": [...]}],
  "hierarchy": [{"meta_theme": "...", "description": "...", "child_themes": [...]}],
  "strategic_insights": ["insight 1", "insight 2"],
  "timings": {"phase1_generate_items": 12.3, ...}
}
```

## Design Notes

- **No embeddings**: Clustering is done via LLM-based semantic grouping (Haiku), not vector embeddings. This keeps the protocol dependency-free and leverages the LLM's understanding of semantic relationships.
- **Misplacement detection**: Phase 3 explicitly checks for items that may have been misclustered, improving cluster quality.
- **Meta-themes**: Phase 4 builds a two-level hierarchy (meta-themes containing themes), revealing the structure of collective thinking.
