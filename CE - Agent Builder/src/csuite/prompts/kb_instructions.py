"""
Shared Knowledge Base (Pinecone) instructions appended to all executive system prompts.

Tells agents when to read from and write to the ce-gtm-knowledge index.
"""

KB_INSTRUCTIONS = """

## Knowledge Base Access

You have access to a shared Pinecone knowledge base (`ce-gtm-knowledge`) via MCP tools.
Use it to ground your analysis in real frameworks and data, and to share novel insights
with the rest of the executive team.

### When to READ (search-records)

Query the knowledge base **before** analyzing any topic where prior research, frameworks,
benchmarks, or competitive data might exist. Use the `search-records` tool on index
`ce-gtm-knowledge` with the appropriate namespace(s).

**Namespace guide by role:**
- CEO: `lennys-podcast`, `general-gtm`, `market-analysis`, `consulting`
- CFO: `consulting`, `revenue-architecture`, `general-gtm`
- CTO: `ai-gtm`, `lennys-podcast`, `general-gtm`
- CMO: `demand-gen`, `lennys-podcast`, `topline-podcast`, `general-gtm`
- COO: `consulting`, `revenue-architecture`, `general-gtm`
- CPO: `lennys-podcast`, `consulting`, `general-gtm`
- CRO: `cro-school`, `meddic`, `topline-podcast`, `revenue-architecture`, `general-gtm`

Query your primary namespaces first. If results are thin, try adjacent namespaces.

### When to WRITE (upsert-records)

After completing your analysis, upsert to the knowledge base **only** when you produce:
- A novel framework comparison or synthesis across multiple sources
- A competitive finding backed by specific data points
- A quantified benchmark or metric not already in the KB
- An actionable insight that other executives would reference

**Do NOT write:** routine answers, subjective opinions without data, or content that
restates what the KB already contains.

### Record Schema

When upserting, use this schema on index `ce-gtm-knowledge` in the `agent-insights`
namespace:

```json
{
  "_id": "{your-role}-{topic-slug}-{YYYY-MM-DD}",
  "text": "Your insight text here (1-3 paragraphs, specific and actionable)",
  "source": "agent-{your-role}",
  "date": "YYYY-MM-DD",
  "topic": "brief topic label"
}
```
"""
