# External Integrations

Reference document for all external APIs, databases, auth providers, and third-party services used across the CE-AGENTS monorepo.

---

## LLM Providers

### Anthropic (Primary)

- **SDK**: `anthropic>=0.83.0` (AsyncAnthropic)
- **Auth**: `ANTHROPIC_API_KEY` in `.env`
- **Models**: `claude-opus-4-6` (executive agents), `claude-haiku-4-5-20251001` (orchestration)
- **Features used**: Extended thinking (budget_tokens), tool use / function calling, prompt caching
- **Used by**: All projects (Agent Builder, Orchestration, Evals)
- **Source**: `CE - Agent Builder/src/csuite/agents/base.py`, `CE - Multi-Agent Orchestration/protocols/llm.py`

### OpenAI

- **SDK**: `openai>=1.0`
- **Auth**: `OPENAI_API_KEY` in `.env`
- **Models**: GPT Image 1 (image generation), GPT-4 (eval judge backend)
- **Used by**: Agent Builder (CMO/CPO image generation), Evals (judge backend)
- **Source**: `CE - Agent Builder/src/csuite/tools/image_gen.py`, `CE - Evals/src/ce_evals/core/judge_backends.py`

### Google Gemini

- **SDK**: `google-genai>=1.0`
- **Auth**: `GEMINI_API_KEY` / `GOOGLE_API_KEY` in `.env`
- **Models**: Imagen 3 (image generation), Gemini (eval judge backend)
- **Used by**: Agent Builder (CMO/CPO image generation), Evals (judge backend)
- **Source**: `CE - Agent Builder/src/csuite/tools/image_gen.py`, `CE - Evals/src/ce_evals/core/judge_backends.py`

### LiteLLM (Multi-Provider Router)

- **SDK**: `litellm>=1.40.0`
- **Auth**: Routes to provider-specific keys automatically
- **Purpose**: Enables per-agent model overrides (e.g., `gemini/gemini-3.1-pro-preview`) without changing orchestrator code
- **Used by**: Multi-Agent Orchestration
- **Source**: `CE - Multi-Agent Orchestration/protocols/llm.py`

## Vector Databases

### Pinecone

- **SDK**: `pinecone[grpc]>=5.0.0` (Agent Builder), `pinecone>=5.0.0` (Orchestration)
- **Auth**: `PINECONE_API_KEY` in `.env`
- **Indexes**:
  - `ce-gtm-knowledge` (via `PINECONE_INDEX_HOST`) -- GTM knowledge base, shared by all agents
  - `ce-c-suite-learning` (via `PINECONE_LEARNING_INDEX_HOST`) -- Agent semantic memory, one namespace per role
- **Features**: Integrated inference (no local embedding model), GRPC transport
- **MCP Access**: Also available via `@pinecone-database/mcp` npx package (stdio transport) for SDK agents
- **Used by**: Agent Builder (knowledge base + memory), Orchestration (paper ingestion)
- **Source**: `CE - Agent Builder/src/csuite/tools/pinecone_kb.py`, `CE - Agent Builder/src/csuite/memory/store.py`, `CE - Agent Builder/src/csuite/agents/mcp_config.py`
- **Graceful degradation**: Memory disabled if keys not configured; set `MEMORY_ENABLED=false` to disable explicitly

## Relational Databases

### PostgreSQL 16

- **Driver**: `asyncpg>=0.29` via `sqlalchemy[asyncio]>=2.0`
- **Auth**: `DATABASE_URL=postgresql+asyncpg://ce:ce_local@localhost:5432/ce_platform`
- **Infrastructure**: Docker Compose service at repo root
- **Migrations**: Alembic (`ce-db/alembic.ini`)
- **Tables**:
  - `runs` -- Protocol run metadata, cost tracking, Langfuse trace IDs
  - `agent_outputs` -- Per-agent output per run (linked to `runs` via FK)
  - `eval_runs` -- Evaluation results with judge scores
  - `eval_samples` -- Per-candidate measurement rows for quality economics
  - `eval_regressions` -- Precomputed regression deltas against baselines
- **Used by**: Orchestration (persistence), Evals (score storage), ce-db (shared layer)
- **Source**: `ce-db/src/ce_db/models/runs.py`, `ce-db/src/ce_db/models/evals.py`, `ce-db/src/ce_db/engine.py`
- **Graceful degradation**: Persistence is best-effort; reports `PersistOutcome.warnings` if DB unavailable

### DuckDB

- **SDK**: `duckdb>=1.0.0`
- **Auth**: None (local file)
- **Path**: `data/agent_memory.duckdb` (configurable via `DUCKDB_PATH`)
- **Purpose**: Agent state storage (experience logs, user preferences, session metadata). NOT for vector memories.
- **Used by**: Agent Builder only
- **Source**: `CE - Agent Builder/src/csuite/storage/duckdb_store.py`

### SQLite (API Layer)

- **SDK**: `sqlmodel>=0.0.14` (SQLAlchemy + Pydantic)
- **Purpose**: Local database for FastAPI Orchestrator UI backend
- **Used by**: Orchestration API
- **Source**: `CE - Multi-Agent Orchestration/api/database.py`

## Observability

### Langfuse (Tracing and Evaluation)

- **SDK**: `langfuse>=2.0.0` (SDK v3 API)
- **Auth**: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL` / `LANGFUSE_HOST`
- **Deployment**: Langfuse Cloud (`us.cloud.langfuse.com`); self-hosted config commented out in `docker-compose.yml`
- **Features used**:
  - Protocol-level traces via `@trace_protocol` decorator
  - Generation spans with input/output content for LLM-as-Judge evals
  - Datasets and dataset items for benchmark experiments
  - Numeric scores on traces (`create_score()`)
  - Session grouping and user attribution
- **API quirks (SDK v3)**: `start_span()` cannot set tags/session_id; must use ingestion API (`TraceBody`). `start_generation()` deprecated in favor of `start_observation(as_type="generation")`. `usage=` renamed to `usage_details=`.
- **Used by**: Multi-Agent Orchestration (all 48+ protocols)
- **Source**: `CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py`
- **Graceful degradation**: All tracing is no-op if `LANGFUSE_SECRET_KEY` not set

### Metabase (Analytics Dashboard)

- **Deployment**: Docker Compose service, port 3001
- **Backend**: Reads from the same `ce_platform` Postgres database
- **Auth**: Own user DB stored in `metabase` database within the same Postgres instance
- **Used for**: Visualizing protocol run data, cost trends, evaluation scores

## Government Data APIs

### SEC EDGAR

- **Auth**: None required (User-Agent header mandatory)
- **Rate limit**: 10 requests/second, no daily limit
- **Endpoints**: Company search by CIK/ticker, filing retrieval (10-K, 10-Q, Form D, S-1, 13-F), XBRL financial data
- **Available via**: Direct Python client (`tools/sec_edgar.py`) AND custom MCP server (`mcp_servers/sec_edgar_mcp/`)
- **Agent access**: CFO, CRO, and their direct reports
- **Source**: `CE - Agent Builder/src/csuite/tools/sec_edgar.py`, `CE - Agent Builder/mcp_servers/sec_edgar_mcp/`

### US Census Bureau

- **Auth**: Optional free API key (500 queries/day without, unlimited with)
- **Endpoints**: County Business Patterns, Annual Business Survey, ZIP Code Business Patterns
- **Used for**: Market sizing, industry benchmarks, business counts
- **Source**: `CE - Agent Builder/src/csuite/tools/census_api.py`

### Bureau of Labor Statistics (BLS)

- **Auth**: Optional free API key (25 queries/day without, 500 with)
- **Endpoints**: QCEW (employment/wages), OES (occupation data), CPI (inflation)
- **Used for**: Industry health assessment, labor cost benchmarking
- **Source**: `CE - Agent Builder/src/csuite/tools/bls_api.py`

## SaaS Integrations

### Notion

- **Auth**: `NOTION_API_KEY` / `NOTION_TOKEN` (integration token)
- **API version**: 2022-06-28
- **Available via**: Direct Python client (`tools/notion_api.py`) AND Notion MCP server (`https://mcp.notion.com/mcp`, HTTP transport)
- **Capabilities**: Search, database queries, page creation/read
- **Agent access**: All agents (COO is primary user)
- **Source**: `CE - Agent Builder/src/csuite/tools/notion_api.py`, `CE - Agent Builder/src/csuite/agents/mcp_config.py`

### GitHub

- **Auth**: `GITHUB_TOKEN` (personal access token)
- **Rate limit**: 60 req/hr without token, 5,000 req/hr with token
- **Available via**: Direct Python client (`tools/github_api.py`) AND custom MCP server (`mcp_servers/github_intel_mcp/`)
- **Capabilities**: Org metadata, repo languages, contributors, commit activity, engineering maturity assessment
- **Agent access**: CTO and CTO direct reports (audit-architect, ai-systems-designer, internal-platform, R&D team)
- **Source**: `CE - Agent Builder/src/csuite/tools/github_api.py`, `CE - Agent Builder/mcp_servers/github_intel_mcp/`

### Brave Search

- **Auth**: `BRAVE_API_KEY`
- **Rate limit**: Free tier 2K queries/month, 1 req/sec
- **Capabilities**: Web search with result snippets, URL content fetching
- **Agent access**: All agents
- **Source**: `CE - Agent Builder/src/csuite/tools/web_search.py`

### QuickBooks (STUB -- Not Functional)

- **Auth**: `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET`, `QUICKBOOKS_REFRESH_TOKEN`, `QUICKBOOKS_REALM_ID`
- **Status**: Dead stub -- dataclass interface only, no OAuth flow implemented, not wired into tool registry
- **Intended for**: CFO agent financial data access
- **Source**: `CE - Agent Builder/src/csuite/tools/quickbooks_mcp.py`

### Google Workspace

- **Auth**: `GOOGLE_CREDENTIALS_PATH` pointing to `credentials/google-credentials.json`
- **Status**: Config exists but minimal integration surface
- **Intended for**: All agents (workspace document access)

## Workflow Automation

### n8n

- **Directory**: `n8n Workflows/`
- **Workflow files**:
  - `p22-sequential-pipeline.json` -- Sequential pipeline protocol automation
  - `p17-red-blue-white.json` -- Red/Blue/White team protocol automation
- **Purpose**: External workflow automation for protocol execution
- **Integration**: JSON exports imported into n8n instance (not managed in-repo)

## API Layer (Internal)

### FastAPI Orchestrator API

- **Framework**: FastAPI with Uvicorn ASGI server
- **Port**: Default Uvicorn port
- **Auth**: API key via `X-API-Key` header; skippable in dev (`SKIP_AUTH=true`)
- **CORS**: Allowed origins: `localhost:5173`, `localhost:5174` (Vite dev server)
- **Streaming**: SSE via `sse-starlette` for live protocol run updates
- **Routers**: agents, integrations, knowledge, pipelines, protocols, runs, teams
- **Source**: `CE - Multi-Agent Orchestration/api/server.py`

## MCP Server Assignment Matrix

Which agents get which MCP servers (configured in `CE - Agent Builder/src/csuite/agents/mcp_config.py`):

| MCP Server | Agents |
|------------|--------|
| Pinecone | ALL agents (via `_COMMON`) |
| Notion | ALL agents (via `_COMMON`) |
| SEC EDGAR | CFO, CRO, CFO direct reports, CRO/GTM sales agents, revenue-analyst |
| Pricing Calculator | CFO, CRO, CFO direct reports, CRO/GTM sales agents |
| GitHub Intel | CTO, CTO direct reports, CTO R&D team |

## Resilience Patterns

External API calls in Agent Builder use resilience decorators from `CE - Agent Builder/src/csuite/tools/resilience.py`:

- **Retry with exponential backoff + jitter** on transient errors (rate limits, 5xx, connection errors)
- **TTL-based response cache** for repeated queries
- **Circuit breaker** to prevent cascading failures

Orchestration LLM calls (`protocols/llm.py`) use a separate retry helper:
- 4 total attempts with delays of 1s, 2s, 4s + up to 0.5s jitter
- Retries on `RateLimitError`, `APIConnectionError`, and 5xx status codes

## Environment Variable Summary

| Variable | Required | Used By |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | All projects |
| `DATABASE_URL` | No (has default) | ce-db, Orchestration persistence |
| `LANGFUSE_SECRET_KEY` | No | Orchestration tracing |
| `LANGFUSE_PUBLIC_KEY` | No | Orchestration tracing |
| `LANGFUSE_HOST` / `LANGFUSE_BASE_URL` | No | Orchestration tracing |
| `PINECONE_API_KEY` | No | Agent Builder KB + memory |
| `PINECONE_INDEX_HOST` | No | Agent Builder GTM knowledge base |
| `PINECONE_LEARNING_INDEX_HOST` | No | Agent Builder semantic memory |
| `NOTION_API_KEY` / `NOTION_TOKEN` | No | Agent Builder Notion tools |
| `GITHUB_TOKEN` | No | Agent Builder GitHub tools |
| `BRAVE_API_KEY` | No | Agent Builder web search |
| `OPENAI_API_KEY` | No | Agent Builder image gen, Evals judge |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | No | Agent Builder image gen, Evals judge |
| `GOOGLE_CREDENTIALS_PATH` | No | Agent Builder Google Workspace |
| `QUICKBOOKS_CLIENT_ID` | No | Agent Builder (stub) |
| `QUICKBOOKS_CLIENT_SECRET` | No | Agent Builder (stub) |
| `QUICKBOOKS_REFRESH_TOKEN` | No | Agent Builder (stub) |
| `QUICKBOOKS_REALM_ID` | No | Agent Builder (stub) |
| `AGENT_BACKEND` | No (default: legacy) | Agent Builder backend selection |
| `AGENT_MODE` | No (default: production) | Orchestration agent mode |
| `MEMORY_ENABLED` | No (default: true) | Agent Builder memory toggle |
| `API_KEY` | No | Orchestration API auth |
| `SKIP_AUTH` | No (default: true) | Orchestration API auth bypass |
| `DUCKDB_PATH` | No | Agent Builder local DB path |
| `DEFAULT_MODEL` | No | Agent Builder model override |
