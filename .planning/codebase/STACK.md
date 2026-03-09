# Technology Stack

Reference document for the CE-AGENTS monorepo technology stack. Covers languages, runtimes, frameworks, build systems, and configuration across all sub-projects.

---

## Languages and Runtimes

| Language | Version | Where Used |
|----------|---------|------------|
| Python | >=3.11 (CI runs 3.13) | Agent Builder, Multi-Agent Orchestration, Evals, ce-db |
| TypeScript | ~5.9.3 | Orchestration UI (`CE - Multi-Agent Orchestration/ui/`) |
| Node.js | 20 (CI) | Orchestration UI build tooling |
| SQL | PostgreSQL 16 dialect | ce-db migrations, Metabase queries |

## Python Frameworks and Core Libraries

### Across All Projects

| Library | Version | Purpose |
|---------|---------|---------|
| `anthropic` | >=0.83.0 | Anthropic Claude API (AsyncAnthropic) |
| `pydantic` | >=2.0 | Data models and validation |
| `pydantic-settings` | >=2.0 | Environment-based configuration |
| `python-dotenv` | >=1.0.0 | `.env` file loading |

### CE - Agent Builder (`CE - Agent Builder/pyproject.toml`)

| Library | Version | Purpose |
|---------|---------|---------|
| `click` | >=8.1.0 | CLI framework |
| `rich` | >=13.0.0 | Terminal output (panels, markdown, tables, spinners) |
| `httpx` | >=0.27.0 | Async HTTP client for external APIs |
| `duckdb` | >=1.0.0 | Local embedded DB for agent state (memory, sessions, preferences) |
| `pinecone[grpc]` | >=5.0.0 | Vector knowledge base and semantic memory |
| `aiofiles` | >=24.0.0 | Async file I/O |
| `claude-agent-sdk` | >=0.1.0 | Agent SDK backend (optional `[sdk]` extra) |

### CE - Multi-Agent Orchestration (`CE - Multi-Agent Orchestration/requirements.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| `litellm` | >=1.40.0 | Multi-provider LLM routing (OpenAI, Gemini, Anthropic) |
| `langfuse` | >=2.0.0 | Observability and tracing (SDK v3) |
| `pyyaml` | >=6.0 | YAML config parsing |
| `PyMuPDF` | >=1.25.0 | PDF ingestion for research papers |
| `pinecone` | >=5.0.0 | Vector search for paper ingestion |

### CE - Multi-Agent Orchestration API (`CE - Multi-Agent Orchestration/api/requirements.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.104.0 | REST API framework |
| `uvicorn[standard]` | >=0.24.0 | ASGI server |
| `sqlmodel` | >=0.0.14 | SQLAlchemy + Pydantic ORM for API models |
| `sse-starlette` | >=1.8.0 | Server-Sent Events for streaming protocol runs |

### CE - Evals (`CE - Evals/pyproject.toml`)

| Library | Version | Purpose |
|---------|---------|---------|
| `openai` | >=1.0 | GPT-4 judge backend |
| `google-genai` | >=1.0 | Gemini judge backend |
| `pyyaml` | >=6.0 | Rubric loading |

### ce-db (`ce-db/pyproject.toml`)

| Library | Version | Purpose |
|---------|---------|---------|
| `sqlalchemy[asyncio]` | >=2.0 | Async ORM and query builder |
| `asyncpg` | >=0.29 | PostgreSQL async driver |
| `alembic` | >=1.13 | Database schema migrations |

### Demo App (`CE - Agent Builder/demo/requirements.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| `streamlit` | >=1.40.0 | Web UI for prospect research demo |
| `pandas` | >=2.0.0 | Data manipulation for demo tables |

## Frontend Stack (Orchestration UI)

Source: `CE - Multi-Agent Orchestration/ui/package.json`

| Library | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.2.0 | UI framework |
| `react-dom` | ^19.2.0 | React DOM renderer |
| `react-router-dom` | ^7.13.1 | Client-side routing |
| `zustand` | ^5.0.11 | State management |
| `recharts` | ^3.7.0 | Data visualization / charts |
| `mermaid` | ^11.12.3 | Protocol diagram rendering |
| `react-markdown` | ^10.1.0 | Markdown rendering |
| `remark-gfm` | ^4.0.1 | GitHub Flavored Markdown support |
| `@headlessui/react` | ^2.2.9 | Accessible UI components |
| `tailwindcss` | ^4.2.1 | Utility-first CSS framework |
| `vite` | ^7.3.1 | Build tool and dev server |
| `vitest` | ^4.0.18 | Test framework |
| `typescript` | ~5.9.3 | Type checking |
| `eslint` | ^9.39.1 | Linting |

## MCP Servers (Agent Builder)

Three custom Model Context Protocol servers in `CE - Agent Builder/mcp_servers/`:

| Server | Directory | Transport | Dependencies |
|--------|-----------|-----------|--------------|
| SEC EDGAR | `sec_edgar_mcp/` | stdio | `mcp>=1.0.0`, `httpx` |
| Pricing Calculator | `pricing_mcp/` | stdio | `mcp>=1.0.0` |
| GitHub Intel | `github_intel_mcp/` | stdio | `mcp>=1.0.0`, `httpx` |

External MCP services consumed:
- **Pinecone MCP** -- via `npx -y @pinecone-database/mcp` (stdio transport)
- **Notion MCP** -- via `https://mcp.notion.com/mcp` (HTTP transport)

All servers built with hatchling build system.

## Build Systems

| Project | Build Backend | Config File |
|---------|--------------|-------------|
| CE - Agent Builder | hatchling | `pyproject.toml` |
| CE - Evals | setuptools (>=68.0) | `pyproject.toml` |
| ce-db | setuptools (>=68.0) | `pyproject.toml` |
| MCP Servers (3) | hatchling | `pyproject.toml` each |
| Orchestration UI | Vite 7 + TypeScript | `package.json` + `tsconfig` |

## Linting and Type Checking

| Tool | Config | Rules |
|------|--------|-------|
| `ruff` | `CE - Agent Builder/pyproject.toml` | E, F, I, N, W, UP; line-length 100; target py311 |
| `mypy` | `CE - Agent Builder/pyproject.toml` | `check_untyped_defs=true`, not strict; broad error suppression for tool modules |
| `eslint` | `CE - Multi-Agent Orchestration/ui/` | React hooks + refresh plugins |

## Testing

| Framework | Project | Config |
|-----------|---------|--------|
| `pytest` >=8.0 | Agent Builder, Evals, ce-db | `asyncio_mode = "auto"`, marker `integration` for real API calls |
| `pytest` | Orchestration | installed ad-hoc in CI |
| `vitest` ^4.0 | Orchestration UI | with `@testing-library/react` |

CI runs `-m "not integration"` by default. Integration tests require live API keys.

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` with 5 jobs:

1. **Agent Builder -- Lint**: ruff + mypy on `src/csuite`
2. **Agent Builder -- Tests**: pytest (non-integration) with placeholder API key
3. **Orchestration -- Lint**: ruff on `protocols/` + `api/`
4. **Orchestration -- Tests**: pytest with placeholder API key
5. **Orchestration -- UI Build**: `npm ci && npx vite build`

All jobs run on `ubuntu-latest` with Python 3.13 / Node 20. Triggered on push/PR to `main`.

## Infrastructure (Docker)

`docker-compose.yml` at repo root:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | `postgres:16` | 5432 | Shared database (runs, evals, agent outputs) |
| `metabase` | `metabase/metabase:latest` | 3001 | Analytics dashboard on top of Postgres |

Langfuse self-hosted config is commented out in docker-compose (using Langfuse Cloud instead).

Database: `ce_platform`, user: `ce`, password: `ce_local` (local dev defaults).

## Configuration Files

| File | Scope | Purpose |
|------|-------|---------|
| `.env.example` (root) | Monorepo | Core keys: Anthropic, Langfuse, Postgres, optional integrations |
| `CE - Agent Builder/.env.example` | Agent Builder | Full agent config: all API keys, DuckDB path, memory, backend selection |
| `CE - Multi-Agent Orchestration/.env.example` | Orchestration | Anthropic + optional Pinecone |
| `CE - Agent Builder/demo/.env.example` | Demo | Minimal Anthropic key for Streamlit demo |
| `ce-db/alembic.ini` | ce-db | Alembic migration config pointing to `ce_platform` |

## Model Policy

| Tier | Model ID | Usage |
|------|----------|-------|
| Thinking/Executive | `claude-opus-4-6` | All 7 executive agents, strategic reasoning, synthesis |
| Orchestration/Mechanical | `claude-haiku-4-5-20251001` | Dedup, ranking, extraction, classification steps |

Temperature varies by role: CFO=0.5, CEO/CTO/COO/CPO=0.6, CMO=0.8.

Agent model can be overridden via `--agent-model` flag; routes through LiteLLM for non-Anthropic models (e.g., `gemini/gemini-3.1-pro-preview`).
