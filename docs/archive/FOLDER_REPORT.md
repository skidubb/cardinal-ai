# CE - AGENTS — Folder Report

**Owner:** Scott Ewalt / Cardinal Element
**Repo name:** `cardinal-ai`
**Reported:** May 14, 2026
**Size on disk:** ~7.8 GB
**Top-level entries:** 23 directories, 25 files

Cardinal Element's agentic AI monorepo. Consolidates three previously separate repos (`ce-c-suite`, `coordination-lab`, `CE-Evals`) plus a Next.js customer portal, shared infrastructure packages, and automation workflows. Cardinal Element is an AI-native growth-architecture consultancy and this folder is its production workspace.

---

## 1. Top-Level Layout

```
CE - AGENTS/
├── CE - Agent Builder/              C-Suite CLI — 7 executive agents, tools, memory
├── CE - Multi-Agent Orchestration/  62 protocols + FastAPI/React web UI
├── CE - Evals/                      LLM-as-judge evaluation framework
├── CE - Recursive Loops/            Recursive loop patterns
├── Multi-Agent Research/            Research notes and experiments
├── cardinal-portal/                 Next.js 16 customer portal (Clerk + Vercel)
├── ce-shared/                       Shared pricing + env registry (Python)
├── ce-db/                           Shared Postgres schema + Alembic migrations
├── ce-graph/                        Multi-tenant knowledge graph (Graphiti + FalkorDB)
├── n8n Workflows/                   Automation workflow exports
├── Scripts/                         Utility scripts (incl. dev-bootstrap.sh)
├── content/                         Marketing / content assets
├── docs/                            Documentation
├── db-init/                         Database init scripts
├── presentations/                   Decks
└── Shared/                          Cross-project shared resources
```

Root files of note: `CLAUDE.md`, `README.md`, `Dockerfile`, `docker-compose.yml`, `Makefile`, `railway.toml`, `architecture.html`, `ce-architecture-diagram.html`, `ce-analytics-dashboard.jsx`, `agent-console-definitions.yaml` (~616 KB), `agent-console-robust.yaml` (~632 KB), `CE_AGENTS_COORDINATION_LEARNING_SPEC.md`, `RECOMMENDATION-collective-intelligence-layer.md`, `gtm_demo_picks.md`.

---

## 2. Core Projects

### CE - Agent Builder — *the agent factory*

A Python CLI app (`csuite`) hosting 7 executive AI agents — CEO, CFO, CTO, CMO, COO, CPO, CRO — with role-specific tools, MCP integrations, and Pinecone memory.

- 80 role system prompts in `agents/sdk_agent.py:_ROLE_PROMPTS`
- 27 tool schemas in `tools/schemas.py:ALL_TOOL_SCHEMAS`
- Per-role tool mappings for 66 roles in `tools/registry.py`
- Two backends: `BaseAgent` (direct Anthropic API tool loop) and `SdkAgent` (Claude Agent SDK subprocess)
- DuckDB learning store, session persistence, evaluation reports (`evaluation-v2-*`)
- Setup: `pip install -e ".[dev]"` (hatchling)

Sample commands: `csuite ceo "question"`, `csuite synthesize -a cfo cto`, `csuite debate -a cfo cto cmo -r 3`, `csuite audit --revenue "$12M" --employees 45`.

### CE - Multi-Agent Orchestration — *the protocol engine*

57 coordination protocols (62 protocol directories on disk) and a 62-agent registry exposed through a FastAPI engine with a React front-end. Each protocol is a self-contained module: `orchestrator.py`, `prompts.py`, `run.py`.

Protocol categories include Liberating Structures, intelligence tradecraft (ACH, etc.), TRIZ, game theory, systems thinking, philosophical reasoning, multi-round debate, and **Decentralized Coordination** (P53–P57: Contract Net, Blackboard, Gossip Consensus, Stigmergic Exploration, Liquid Democracy).

Production-deployment notes:
- `ServerAgent` (in `protocols/server_agent.py`) is the Docker-safe agent class — direct `AsyncAnthropic` + native tool-use loop, max 15 iterations.
- Two model tiers: Opus for reasoning, Haiku for orchestration / mechanical steps.
- `--mode research` falls back to lightweight dicts; production is default.
- Web UI: FastAPI + React with SSE streaming and WeasyPrint PDF reports.
- Observability: Langfuse tracing (`@trace_protocol`) and Postgres persistence, both degrading gracefully.

### CE - Evals

Library-only LLM-as-judge framework. No CLI — imported programmatically. Backends in `src/ce_evals/core/judge_backends.py` cover Claude, GPT-4, and Gemini, with shared `rubric.py`, `runner.py`, and `cost.py`.

### cardinal-portal — *the customer surface*

Next.js 16 (App Router) + Clerk (auth, Organizations, Billing) + shadcn + Tailwind 4. Deployed to Vercel. Owns sign-in/sign-up/MFA, member management, Stripe subscriptions, dashboards, connector setup wizard, query UI, and the CE admin console.

Communicates with the Railway backend via Clerk-issued JWTs. The `org.slug` claim flows through to the FastAPI engine, where `api/middleware/clerk_auth.py` validates and scopes every operation to that tenant's FalkorDB graph + Pinecone namespace.

### CE - Recursive Loops

Recursive loop patterns for iterative agent workflows. Placeholder/scaffold directory.

### Multi-Agent Research

Research notes, experiments, and reference materials supporting protocol design.

---

## 3. Shared Packages

| Package | Purpose |
|---|---|
| **ce-shared** | Single source of truth for `MODEL_PRICING`, `cost_for_model()`, `KEY_REGISTRY`, `find_and_load_dotenv()`. Used by every Python project. |
| **ce-db** | Async SQLAlchemy + asyncpg + Alembic. Postgres schema for runs, traces, costs. Used by Orchestration and (optionally) Evals. |
| **ce-graph** | Multi-tenant knowledge graph layer over Graphiti + FalkorDB. Entity types: `Client`, `Engagement`, `Protocol`, `Decision`, `Correction`, `Lesson`. Each customer = own FalkorDB graph. CLI: `cegraph list/status/init/create/drop`. Six canonical tenants provisioned: `cardinal-element`, `imagine-wireless`, `workload`, `silver-lake-auto`, `public-safety-wireless`, `on3`. Additional tenants auto-provisioned from Clerk Organizations. See `ce-graph/SETUP.md` and `ce-graph/ONBOARDING.md`. |

---

## 4. Productization Architecture

The product is split into two halves communicating via Clerk JWTs:

- **Vercel (cardinal-portal)** — owns auth, billing, tenant identity, customer-facing UX.
- **Railway (CE - Multi-Agent Orchestration/api/)** — owns protocol execution, ce-graph queries, ingest workers, cost tracking. Validates the Clerk JWT, extracts `org_slug`, scopes everything per-tenant.

Tenant identity flow: Clerk Organization → `org.slug` → ce-graph tenant slug. Runs persisted with a `tenant_id` scoping column so a single DB stays cleanly partitioned per customer.

Deployment: Railway.app from branch `claude/add-rc-config-support-W9iw7`. Multi-stage Dockerfile (Node build for React UI → Python runtime with cairo/pango for WeasyPrint). Railway Postgres addon. Healthcheck at `/api/health`.

---

## 5. Supporting Material at Root

- `architecture.html`, `ce-architecture-diagram.html` — visual architecture references
- `ce-analytics-dashboard.jsx` — analytics dashboard component
- `agent-console-definitions.yaml` / `agent-console-robust.yaml` — large (~600 KB each) agent console configs
- `CE_AGENTS_COORDINATION_LEARNING_SPEC.md` — coordination learning spec
- `RECOMMENDATION-collective-intelligence-layer.md` — design recommendation memo
- `gtm_demo_picks.md` — go-to-market demo selections
- `n8n Workflows/` — JSON exports for n8n automation pipelines
- `presentations/`, `content/` — decks and marketing material (includes a Chargie pitch-deck archive under `CE - Agent Builder/_archive/`)
- `docs/local-dev.md` — local-dev playbook
- `scripts/dev-bootstrap.sh` — idempotent fresh-machine setup

---

## 6. Conventions

- **Python 3.11+** across all Python projects, each with its own venv
- **Async everywhere** — `AsyncAnthropic`, `asyncio.gather`, `async def`
- **Ruff** lint (E, F, I, N, W, UP; line length 100)
- **mypy** with `check_untyped_defs` (not strict)
- **Pydantic v2** for models/settings
- **Tests** — `@pytest.mark.integration` for real API calls; CI runs `-m "not integration"`
- **Model policy** — `claude-opus-4-7` for executive reasoning, `claude-haiku-4-5-20251001` for orchestration / mechanical steps
- **Protocol naming** — `p{NN}_{descriptor}` (e.g., `p06_triz`, `p16_ach`)
- **Agent keys** — kebab-case (e.g., `ceo-board-prep`, `gtm-vp-sales`)

Environment: each project takes a `.env` with at minimum `ANTHROPIC_API_KEY` (copy from `.env.example`). Pinecone, Notion, and other integrations are optional and degrade gracefully.

---

## 7. Headline Numbers

| Metric | Count |
|---|---:|
| Top-level directories | 23 |
| Top-level files | 25 |
| Folder size on disk | ~7.8 GB |
| Coordination protocols | 57 (62 dirs incl. variants) |
| Agent registry size | 62 agents across 14 categories |
| Executive agent roles | 7 |
| Role system prompts | 80 |
| Tool schemas | 27 |
| Provisioned ce-graph tenants | 6 canonical + Clerk-driven |
| Shared Python packages | 3 (ce-shared, ce-db, ce-graph) |

---

## 8. Documentation Map

Each project has its own detailed `CLAUDE.md`:

- Root `CLAUDE.md` — architecture, commands, conventions, productization stack
- `CE - Agent Builder/.claude/CLAUDE.md` — CLI, agent system architecture, patterns
- `CE - Multi-Agent Orchestration/CLAUDE.md` — protocol architecture, taxonomy, diagram conventions
- `cardinal-portal/CLAUDE.md` + `AGENTS.md` — portal architecture and agent integration notes
- `ce-graph/SETUP.md`, `ce-graph/ONBOARDING.md` — graph setup + tenant provisioning
- `docs/local-dev.md` — local dev options and scenarios
- Productization plan: `~/.claude/plans/are-you-currently-relying-imperative-token.md` (6-milestone roadmap to first paying customer)

---

**TL;DR** — A production-grade multi-agent AI consultancy platform. The agent definitions and tools live in *Agent Builder*; *Multi-Agent Orchestration* runs them through 57 coordination protocols and exposes a web UI; *Evals* QA's the outputs; *ce-shared/ce-db/ce-graph* provide shared infrastructure and per-tenant memory; *cardinal-portal* is the Clerk-authenticated customer surface that fronts it all.
