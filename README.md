# cardinal-ai

Monorepo for Cardinal Element's agentic AI work — agent systems, orchestration protocols, a customer portal, evaluation frameworks, and automation workflows.

See [CLAUDE.md](./CLAUDE.md) for architecture, commands, and conventions. See [docs/local-dev.md](./docs/local-dev.md) for machine setup (or run `bash scripts/dev-bootstrap.sh`).

## Structure

```
CE - AGENTS/
├── CE - Agent Builder/              # C-Suite CLI: 7 executive agents, tools, memory
├── CE - Multi-Agent Orchestration/  # 60 coordination protocols + FastAPI/React web UI
├── CE - Evals/                      # LLM-as-judge evaluation framework
├── cardinal-portal/                 # Next.js 16 customer portal (Clerk + Vercel)
├── ce-shared/                       # Shared pricing + env registry (Python package)
├── ce-db/                           # Shared Postgres schema + Alembic migrations
├── ce-graph/                        # Multi-tenant knowledge graph (Graphiti + FalkorDB)
├── n8n Workflows/                   # n8n automation workflows
└── Scripts/                         # Utility scripts (dev-bootstrap, Notion sync)
```

## Projects

### CE - Agent Builder
C-Suite CLI app — 7 executive AI agents (CEO, CFO, CTO, CMO, COO, CPO, CRO) with per-role tools, MCP integrations, and Pinecone memory. The agent factory: prompts + tools + memory live here; orchestration consumes them via `ServerAgent`.

### CE - Multi-Agent Orchestration
60 multi-agent coordination protocols + 74-agent registry + FastAPI engine. Protocols span Liberating Structures, intelligence tradecraft, game theory, systems thinking, philosophical reasoning, and decentralized coordination. Each protocol is a self-contained module (orchestrator, prompts, CLI). Includes the production web UI deployed on Railway.

### CE - Evals
Library (no CLI) for LLM-as-judge evaluation — Claude, GPT-4, and Gemini judge backends with shared rubric and cost tracking.

### cardinal-portal
Customer + admin web portal. Next.js 16 (App Router) + Clerk (auth, Organizations, Billing) + shadcn + Tailwind 4, deployed to Vercel. Talks to Railway backend via Clerk-issued JWTs; `org.slug` scopes every operation to the right tenant.

### n8n Workflows
n8n workflow definitions (JSON exports) for automation.

### Scripts
Utility scripts — `dev-bootstrap.sh` (one-command local dev setup) and Notion sync tooling.

## Shared Packages

- **`ce-shared/`** — Single source of truth for model pricing (`MODEL_PRICING`) and env-var names (`KEY_REGISTRY`). Used by all Python projects.
- **`ce-db/`** — Async SQLAlchemy + asyncpg + Alembic. Postgres schema for runs, traces, costs.
- **`ce-graph/`** — Knowledge graph layer (Graphiti + FalkorDB). Multi-tenant — each customer is its own graph. CLI: `cegraph list/status/init/create/drop`. See `ce-graph/SETUP.md` and `ce-graph/ONBOARDING.md`.

## Previous Repos

This monorepo consolidates:
- [ce-c-suite](https://github.com/skidubb/ce-c-suite) → `CE - Agent Builder/`
- [coordination-lab](https://github.com/skidubb/coordination-lab) → `CE - Multi-Agent Orchestration/`
- [CE-Evals](https://github.com/skidubb/CE-Evals) → `CE - Evals/`
