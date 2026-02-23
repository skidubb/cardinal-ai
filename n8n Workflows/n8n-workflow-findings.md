# n8n Workflow Build — Findings & Next Steps

## What We Built
- **P22 Sequential Pipeline** (`p22-sequential-pipeline.json`) — 3 sequential agents → quality gate → retry → synthesis
- **P17 Red/Blue/White Team** (`p17-red-blue-white.json`) — parallel red attacks → parallel blue defenses → white adjudication → final assessment

Both are faithful 1:1 translations of the Python protocols into n8n visual workflows using direct Anthropic API calls (HTTP Request nodes with extended thinking).

## What n8n Exposed

### 1. Agents Are Hardcoded
- **24 of 25 protocols** copy-paste the identical `BUILTIN_AGENTS` dict with 7 C-suite personas (CEO, CFO, CTO, CMO, COO, CPO, CRO)
- No shared agent registry exists — every `run.py` has its own copy
- The protocols are supposed to be agent-agnostic (throw ANY agents at them), but the implementation locks them to C-suite

### 2. Agents Have Zero Tools
- No `tool_use`, no `tool_choice`, no function calling anywhere across all 25 protocols
- Agents are pure prompt personas — Claude thinking from a role, with no access to external data
- The only external integration in the entire project is `scripts/ingest_papers.py` (Pinecone ingestion), which is a utility script, not agent tooling

### 3. Agent Count Is Fixed
- P17 hardcodes 2 red + 2 blue + 1 white
- P22 hardcodes 3 sequential stages
- The protocol should handle N agents dynamically

## What Needs to Happen (in the Python protocols, not n8n)

### Agent Registry
- Single `agents.json` or `agents.py` at project root
- Any agent: C-suite, airport operator, city regulator, consultant — defined once, used everywhere
- Each protocol accepts an arbitrary list of agents, any count

### Agent Tools
Agents should have real capabilities, not just opinions:
- **KB Access** — Pinecone `multi-agent-kb` index (academic papers already ingested)
- **Web Search** — live market data, competitor intel, regulatory info
- **API Access** — domain-specific data sources (market data, financial APIs, etc.)
- **Recursive Learning** — agents that can request follow-up research

### Protocol Agnosticism
- Protocols define the *choreography* (who goes when, how outputs flow)
- Agents bring the *capabilities* (persona + tools + knowledge)
- These two concerns should be fully decoupled

## The Bottom Line
n8n proved the protocols work mechanically. It also proved the agents are doing AI theater — no real data, no tools, no dynamic composition. The fix is in `CE - Multi-Agent/protocols/`, not in n8n.
