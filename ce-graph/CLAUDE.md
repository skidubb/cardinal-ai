# CLAUDE.md — ce-graph

Multi-tenant knowledge graph layer (Graphiti + FalkorDB) — shared institutional memory for the C-Suite agents. **Each customer = its own FalkorDB graph.**

Read first: [SETUP.md](SETUP.md) (install, Docker, CLI) and [ONBOARDING.md](ONBOARDING.md) (tenant onboarding).

## Layout

```
src/ce_graph/
├── entities.py         # Client, Engagement, Protocol, Decision, Correction, Lesson
├── tenancy.py          # Tenant slug resolution + isolation
├── graphiti_client.py  # Graphiti wrapper (temporal facts, provenance)
├── falkor_client.py    # FalkorDB connection
├── queries.py          # Cypher query helpers
├── connectors/         # Notion, Granola, Gmail, Slack, Drive ingestion
└── cli.py              # `cegraph list/status/init/create/drop`
```

## Rules

- Six canonical tenants: `cardinal-element`, `imagine-wireless`, `workload`, `silver-lake-auto`, `public-safety-wireless`, `on3`. Additional tenants auto-provision from Clerk Organizations (slug pattern `<base>-<numeric-clerk-id>`).
- Every operation must be tenant-scoped — never query across graphs. Tenant identity flows Clerk Organization → `org.slug` → graph name.
- Local FalkorDB: `docker compose up -d` from this directory.
- Semantic search via `GraphClient.search()`; raw Cypher via `queries.py` helpers.

Conventions per root [CLAUDE.md](../CLAUDE.md).
