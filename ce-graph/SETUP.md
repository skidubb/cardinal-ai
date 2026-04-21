# ce-graph — Setup & Runbook

Knowledge graph layer for Cardinal Element. Built on **Graphiti** (Zep AI) backed by **FalkorDB**. Gives the C-Suite agents shared institutional memory with temporal facts, provenance, and corrections-as-data.

## What you get

- **Shared institutional memory** — every C-Suite agent reads/writes the same graph
- **Temporal facts** — superseded knowledge stays queryable as history
- **Corrections-as-data** — a correction attaches to its scope (Client / Protocol / Agent / Decision) and every future agent action sees it
- **Cross-engagement learning** — patterns from past clients inform new ones
- **Sub-10ms graph queries** via FalkorDB

## One-time install

```bash
cd "/Users/scottewalt/Documents/CE - AGENTS/ce-graph"
python -m venv venv && source venv/bin/activate
pip install -e ".[dev,backfill]"
```

## Stand up FalkorDB locally

```bash
docker compose up -d
docker compose logs -f falkordb     # confirm it's running
```

- **Wire protocol:** `redis://localhost:6379`
- **Browser UI:** http://localhost:3000 (visualize the graph as it grows)

## Configure env

Add to your monorepo `.env`:

```bash
FALKORDB_URL=redis://localhost:6379
FALKORDB_GRAPH_NAME=cardinal_element
GRAPH_LLM_MODEL=claude-haiku-4-5-20251001
# ANTHROPIC_API_KEY already exists
```

For Railway prod (Phase 2): set `FALKORDB_URL` to the Railway FalkorDB service URL.

## Seed the protocols

```bash
python -m ce_graph.scripts.seed_protocols
# OK -- 53 Protocol nodes in graph 'cardinal_element'
```

## Backfill institutional knowledge

**Notion (all workspace databases):**

```bash
python -m ce_graph.scripts.backfill_notion --dry-run     # preview
python -m ce_graph.scripts.backfill_notion --limit 50    # try 50 first
python -m ce_graph.scripts.backfill_notion               # full run
```

Cost estimate: ~$1–5 for 1000 pages (Haiku 4.5 entity extraction).

**Granola (last 6 months of meetings):**

```bash
python -m ce_graph.scripts.backfill_granola --dry-run
python -m ce_graph.scripts.backfill_granola              # last 6 months
python -m ce_graph.scripts.backfill_granola --since 2025-01-01
```

> **Note:** Granola has no public API as of April 2026. The script reads from `~/Library/Application Support/Granola/granola.db` directly. Inspect the schema once with `sqlite3 <db> '.schema'` and adjust column names in `backfill_granola.py:_read_meetings()` if needed.

## Verify

```bash
pytest tests/ -m "not integration"          # unit tests
pytest tests/ -m integration                # requires running FalkorDB
```

Quick interactive check:

```python
from ce_graph.queries import GraphQueries
q = GraphQueries()
print(q.graph_stats())                       # {'Client': N, 'Protocol': 53, ...}
print(q.all_clients())
print(q.decisions_using_protocol('P16'))
```

Hybrid semantic search:

```python
import asyncio
from ce_graph import GraphClient

async def go():
    g = await GraphClient.connect()
    hits = await g.search('what did we recommend about pricing for Acme')
    for h in hits:
        print(h)
    await g.close()

asyncio.run(go())
```

## How agents should use this

In a protocol run, before any C-Suite agent answers:

1. `corrections = q.corrections_applicable_to_client(client_name)` — load the rules-of-the-road for this client
2. `lessons = q.lessons_for_vertical(vertical)` — pull cross-engagement patterns
3. `prior = await graph.search(question)` — semantic recall over past decisions
4. Inject all three into the agent's context window

Wire this in `protocols/server_agent.py` per-turn context assembly.

## Phase 2 (next)

- Cross-agent shared memory bus (engagement-scoped namespaces wired into ServerAgent context assembly)
- Decision Trace nodes auto-written by every protocol run
- Eval scores feed back to graph (close the compounding loop)
- Railway FalkorDB deployment for prod

## Architecture

```
GraphClient (Graphiti + FalkorDB driver + Anthropic Haiku LLM)
   │
   ├── add_episode()   — text in, structured nodes/edges out
   ├── search()        — hybrid semantic + graph traversal
   └── find_*()        — convenience semantic queries

FalkorClient (raw Cypher)
   │
   ├── query()         — execute Cypher
   └── ensure_indexes()— create the indexes our queries need

GraphQueries (deterministic Cypher helpers)
   ├── all_clients()
   ├── corrections_applicable_to_client()
   ├── decisions_using_protocol()
   └── graph_stats()
```

## Files

```
ce-graph/
├── pyproject.toml
├── docker-compose.yml
├── SETUP.md                          (this file)
├── src/ce_graph/
│   ├── __init__.py                   public API
│   ├── entities.py                   Pydantic node models + edge constants
│   ├── falkor_client.py              raw FalkorDB wrapper
│   ├── graphiti_client.py            Graphiti integration
│   └── queries.py                    Cypher query helpers
├── scripts/
│   ├── seed_protocols.py             ingest 55 Protocol nodes
│   ├── backfill_notion.py            ingest Notion workspace
│   └── backfill_granola.py           ingest Granola transcripts (6mo)
└── tests/
    └── test_smoke.py                 unit + integration smoke tests
```
