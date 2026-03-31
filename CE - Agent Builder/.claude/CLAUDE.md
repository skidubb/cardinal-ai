# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

C-Suite Agent Builder is a Python CLI application for building and running AI-powered executive advisory agents (CEO, CFO, CTO, CMO, COO, CPO, CRO) for professional services businesses. Built with the Anthropic API and Click CLI framework, it supports individual agent queries, session persistence, and report generation.

**This repo is exclusively for agent building.** Orchestration code (synthesis, debate, audit, events, evaluation) lives in `CE - Exec Team`.

**Owner:** Scott Ewalt / Cardinal Element -- an AI-native growth architecture consultancy.

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -e .            # Install package + dependencies
pip install -e ".[sdk]"     # Install with Agent SDK backend (optional)
pip install -e ".[dev]"     # Install with dev tools (pytest, ruff, mypy)

# CLI usage
csuite ceo "question"                    # Query individual agent (ceo/cfo/cto/cmo/coo/cpo/cro)
csuite interactive                       # Interactive mode (@ceo, @cfo, @cto, @cmo, @coo, @cpo, @cro)
csuite sessions list                     # List sessions
csuite sessions resume <id>              # Resume session
csuite sessions fork <id> "title"        # Fork a session
csuite report financial --period quarterly --output report.md
csuite report operations --output ops.md
csuite report strategic --output strategy.md
csuite report product --output product.md
csuite report prospect AAPL              # SEC EDGAR prospect brief

# Dev
pytest tests/ -m "not integration"       # Unit tests only (default for CI)
pytest tests/test_foo.py -k "test_name"  # Single test
pytest tests/test_github_api.py -v       # Integration tests (require network, may hit rate limits)
ruff check src/ mcp_servers/              # Lint
mypy src/csuite --ignore-missing-imports # Type check
```

## Architecture

### Two-Layer Agent System

The C-Suite operates as **two parallel agent systems** that serve different purposes:

1. **Claude Code agents** (`~/claude-dotfiles/agents/*.md`) -- Invoked via Claude Code's Task tool. These are the 7 executives (CEO, CFO, CMO, CTO, COO, CPO, CRO) + 30 sub-agents. Executives use `model: opus`; sub-agents use `model: sonnet` or `model: haiku`. Each executive has a DELEGATION section that directs it to recommend sub-agents for execution work.

2. **Python CLI agents** (`src/csuite/`) -- The CLI application with dual backend support. Legacy backend uses `BaseAgent` subclasses with direct Anthropic API calls. SDK backend uses `SdkAgent` with `claude-agent-sdk` and per-role MCP tool access. Both expose `async chat(message) -> str`. All 7 agents (CEO, CFO, CTO, CMO, COO, CPO, CRO) are implemented in both backends.

These two systems are not connected -- the Claude Code agents and the Python CLI agents are independent implementations.

3. **ServerAgent** (`CE - Multi-Agent Orchestration/protocols/server_agent.py`) -- The production agent class for server/Docker deployment. Imports `_ROLE_PROMPTS` from `sdk_agent.py`, `ALL_TOOL_SCHEMAS` and `ROLE_TOOL_MAP` from `tools/`, and dispatches tool calls via `api/tool_executor.py`. Uses direct `anthropic.AsyncAnthropic().messages.create()` with native tool-use loop — no subprocess. This is what runs on Railway.

### Python Application Structure

```
src/csuite/
├── main.py           # Click CLI -- agent queries, sessions, reports, interactive mode
├── config.py         # Settings (pydantic-settings from .env) + AgentConfig per role
├── session.py        # Session/Message models (Pydantic) + SessionManager
├── agents/
│   ├── base.py       # BaseAgent ABC -- conversation management, session handling, API calls, cost tracking, business context loading
│   ├── factory.py    # create_agent() -- routes to BaseAgent or SdkAgent based on AGENT_BACKEND setting
│   ├── sdk_agent.py  # SdkAgent -- Agent SDK backend with per-role MCP tool access
│   ├── mcp_config.py # Per-role MCP server mappings (Pinecone, Notion, SEC EDGAR, Pricing, GitHub Intel)
│   ├── ceo.py        # CEOAgent(BaseAgent) -- ROLE = "ceo", returns CEO_SYSTEM_PROMPT
│   ├── cfo.py        # CFOAgent(BaseAgent) -- same pattern
│   ├── cto.py        # CTOAgent(BaseAgent) -- same pattern
│   ├── cmo.py        # CMOAgent(BaseAgent) -- same pattern
│   ├── coo.py        # COOAgent(BaseAgent) -- same pattern
│   ├── cpo.py        # CPOAgent(BaseAgent) -- same pattern
│   └── cro.py        # CROAgent(BaseAgent) -- same pattern
├── prompts/
│   ├── ceo_prompt.py    # CEO_SYSTEM_PROMPT
│   ├── cfo_prompt.py    # CFO_SYSTEM_PROMPT -- elite prompt with industry-specific frameworks/KPIs
│   ├── cto_prompt.py    # CTO_SYSTEM_PROMPT
│   ├── cmo_prompt.py    # CMO_SYSTEM_PROMPT
│   ├── coo_prompt.py    # COO_SYSTEM_PROMPT
│   ├── cpo_prompt.py    # CPO_SYSTEM_PROMPT
│   ├── cro_prompt.py    # CRO_SYSTEM_PROMPT
│   └── kb_instructions.py   # KB_INSTRUCTIONS -- shared Pinecone read/write guidance appended to all 7 prompts
├── storage/
│   └── duckdb_store.py     # DuckDB-backed storage for non-vector state (experience logs, preferences, sessions)
├── memory/
│   ├── extractor.py        # Memory extraction from conversations
│   └── store.py            # Pinecone-backed semantic memory store (integrated inference, no local embeddings)
├── learning/
│   ├── experience_log.py   # Experience logging for agent learning
│   ├── feedback_loop.py    # Closed-loop learning: self-eval + Pinecone-backed score storage
│   └── preferences.py      # User preference tracking
└── tools/
    ├── schemas.py           # Anthropic tool definitions (input_schema format) for function calling
    ├── registry.py          # Tool registry -- maps agent roles to allowed tools, async handlers, input validation
    ├── cost_tracker.py      # API cost tracking (D10 compliance) -- per-query cost calculation, aggregation by agent/task/time
    ├── resilience.py        # API resilience layer -- exponential backoff, TTL cache, circuit breaker, structured logging
    ├── report_generator.py  # Prospect research brief export (Markdown + optional PDF via weasyprint)
    ├── pricing_calculator.py # Pricing model calculations
    ├── quickbooks_mcp.py    # QuickBooks API wrapper (STUB -- not wired into tool registry, not functional)
    ├── github_api.py        # GitHub API integration
    ├── sec_edgar.py         # SEC EDGAR API for public company filings
    ├── census_api.py        # US Census Bureau API for market sizing
    ├── bls_api.py           # Bureau of Labor Statistics API for labor market data
    ├── qa_protocol.py       # QA protocol tooling
    ├── notion_api.py        # Notion API integration (search, database queries, page creation)
    ├── web_search.py        # Brave Search API + URL fetching
    ├── image_gen.py         # OpenAI GPT Image 1 + Gemini Imagen 3 image generation (CMO/CPO agents)
    └── pinecone_kb.py       # Pinecone knowledge base queries (direct SDK, non-MCP)
```

### Moved to CE - Exec Team

The following modules now live in `/Users/scottewalt/Documents/CE - Exec Team/src/csuite/`:
- `orchestrator.py` -- Multi-agent synthesis
- `debate.py` -- Multi-round debate orchestrator
- `audit.py` -- Growth Strategy Audit pipeline
- `events/` -- Strategy meeting, sprint, board meeting
- `evaluation/` -- Benchmark, judge, report
- `coordination/` -- Constraint negotiation models
- `tracing/` -- Causal graph DAG
- `formatters/` -- Audit formatter, dual output
- `prompts/debate_prompt.py` -- Debate-specific prompts
- `session.py` (debate models) -- DebateSession, DebateArgument, DebateRound, DebateSessionManager

### Demo App

```
demo/
├── app.py        # Streamlit app (prospect research, ICP scoring, agent queries)
└── demo_data.py  # Pre-cached data for ODSC demo mode
```

Imports from `src/csuite/` (not a copy). Run with `streamlit run demo/app.py`.

### Key Patterns

- **Agent creation**: Subclass `BaseAgent`, set `ROLE` class var, implement `get_system_prompt()` returning a prompt constant from `prompts/`. The base class handles API calls, session persistence, cost tracking, and business context injection.
- **Business context**: `BaseAgent._load_business_context()` reads `.claude/CLAUDE.md` and appends it to every system prompt. This is how agents know about the specific business.
- **Session persistence**: JSON files in `sessions/{agent_role}/{session_id}.json`. Sessions are Pydantic models with fork/resume support.
- **Cost tracking**: `CostTracker` logs every API call with per-query costs. Uses February 2026 Anthropic pricing (Opus: $5/$25 per MTok input/output, Sonnet: $3/$15, Haiku: $1/$5).
- **API resilience**: `resilience.py` provides decorators for retry with exponential backoff + jitter, TTL-based response cache, and circuit breaker pattern. Applied to all external API clients (SEC EDGAR, Census, BLS, GitHub).
- **Config**: `Settings` loads from `.env` via pydantic-settings. `get_settings()` is `@lru_cache`-decorated (singleton). `AGENT_CONFIGS` dict maps role -> `AgentConfig` with per-agent model and temperature.
- **DuckDB storage**: `storage/duckdb_store.py` backs experience logs, preferences, and sessions. DB file at `data/agent_memory.duckdb`. Does NOT store vector memories (those are in Pinecone).
- **Tool function calling**: `tools/schemas.py` defines Anthropic-format tool schemas; `tools/registry.py` maps roles to allowed tools and dispatches calls. All tool handlers are async, read-only, and return JSON strings (errors as `{"error": "..."}`).
- **Memory system**: `memory/store.py` uses Pinecone integrated inference (index host via `PINECONE_LEARNING_INDEX_HOST`). Each agent role is a namespace. No local embedding model -- text in, results out.
- **Pinecone knowledge base**: `pinecone[grpc]>=5.0.0` dependency. Index `ce-gtm-knowledge` (via `PINECONE_INDEX_HOST`) is integrated into all SDK agents for GTM context retrieval. Separate from the learning/memory index.
- **Agent SDK backend**: `AGENT_BACKEND=sdk` in `.env` switches from legacy `BaseAgent` subclasses to `SdkAgent` (uses `claude-agent-sdk`). Both expose `async chat(message) -> str`. Factory in `agents/factory.py` selects backend. SDK agents get per-role MCP tool access via `agents/mcp_config.py`. **Known limitation:** SDK backend is stateless (no session persistence) and cost tracking reports total USD but 0 tokens (SDK doesn't expose token counts).
- **MCP servers**: `mcp_servers/` contains 3 custom MCP servers (SEC EDGAR, Pricing Calculator, GitHub Intel) as stdio servers using `Path(__file__)`-based path resolution. `agents/mcp_config.py` maps roles to MCP servers -- all roles get Pinecone + Notion via `_COMMON`; CFO/CRO additionally get SEC EDGAR + Pricing; CTO gets GitHub Intel.
- **KB learning loop**: `prompts/kb_instructions.py` exports `KB_INSTRUCTIONS`, appended to all 7 executive system prompts. Instructs agents to query `ce-gtm-knowledge` Pinecone index before analysis and upsert novel insights to `agent-insights` namespace. Each role has mapped namespaces for reads.
- **Feedback loop**: `learning/feedback_loop.py` implements closed-loop self-evaluation with Pinecone score storage. No user-facing approval/rejection UI.

### Claude Code Agent Inventory

Located at `~/claude-dotfiles/agents/`. Naming convention: `{executive}.md` for executives, `{executive}-{specialty}.md` for sub-agents.

**7 Executives:** `ceo.md`, `cfo.md`, `cmo.md`, `cto.md`, `coo.md`, `cpo.md`, `gtm-cro.md`

**30 Sub-agents:**
- CEO (3): `ceo-deal-strategist.md`, `ceo-competitive-intel.md`, `ceo-board-prep.md`
- CFO (3): `cfo-pricing-strategist.md`, `cfo-cash-flow-forecaster.md`, `cfo-client-profitability.md`
- CMO (6): `cmo-linkedin-ghostwriter.md`, `cmo-thought-leadership.md`, `cmo-outbound-campaign.md`, `cmo-brand-designer.md`, `cmo-distribution-strategist.md`, `cmo-market-intel.md`
- CTO (3): `cto-audit-architect.md`, `cto-ai-systems-designer.md`, `cto-internal-platform.md`
- COO (3): `coo-engagement-manager.md`, `coo-bench-coordinator.md`, `coo-process-builder.md`
- CPO (3): `cpo-service-designer.md`, `cpo-client-insights.md`, `cpo-deliverable-designer.md`
- CRO (9): `gtm-vp-sales.md`, `gtm-vp-growth-ops.md` (renamed from gtm-vp-marketing), `gtm-vp-success.md`, `gtm-vp-revops.md`, `gtm-vp-partnerships.md`, `gtm-sdr-agent.md`, `gtm-deal-desk.md`, `gtm-revenue-analyst.md`, `gtm-partner-enablement.md`

**Also:** `brand-essence.md`, `competitive-ads.md` (standalone tools)

**Note:** Remaining GTM sub-agents (`gtm-sdr-manager.md`, `gtm-ae-strategist.md`, `gtm-sales-ops.md`, `gtm-demand-gen.md`, `gtm-content-marketer.md`, `gtm-abm-specialist.md`, `gtm-data-ops.md`, `gtm-systems-admin.md`, `gtm-channel-marketer.md`, `gtm-alliance-ops.md`, `gtm-renewals-manager.md`, `gtm-csm-lead.md`, `gtm-onboarding-specialist.md`, `gtm-analytics.md`) exist as GTM layer agents that report through CRO's VP structure.

### Model Policy

All executive agents use `claude-opus-4-6`. This is configured in both:
- `config.py` -> `AGENT_CONFIGS` dict (Python app)
- `~/claude-dotfiles/agents/*.md` -> frontmatter `model:` field (Claude Code agents)

Temperature varies by role: CFO=0.5 (precise), CEO/CTO/COO/CPO=0.6 (balanced), CMO=0.8 (creative).

### Testing Conventions

- Tests hitting real APIs (GitHub, SEC EDGAR, Census, BLS) must be marked `@pytest.mark.integration` or use `pytestmark = pytest.mark.integration` at module level.
- CI unit-test job runs with `-m "not integration"` to skip them. Integration tests run separately on push/schedule only.
- `pyproject.toml` registers the marker: `markers = ["integration: real API calls"]`.

## Environment

Requires `.env` file (copy from `.env.example`). Only `ANTHROPIC_API_KEY` is required. Set `AGENT_BACKEND=sdk` to use the Agent SDK backend with MCP tools (default is `legacy`). QuickBooks and GitHub integrations are optional and agent-specific. Memory requires `PINECONE_API_KEY` + `PINECONE_LEARNING_INDEX_HOST`; enabled by default but gracefully degrades if not configured. Disable via `MEMORY_ENABLED=false` in `.env` if needed.

### Gitignored (runtime-only, not in repo)
- `data/`, `sessions/`, `memory/` -- runtime state (DuckDB, session JSON, experience logs)
- `Strategy Meeting/` -- strategy content (managed outside git)
- `scripts/.notion_db_ids.json` -- cached Notion DB IDs

## Style

- Python >=3.11, line length 100
- Ruff rules: E, F, I, N, W, UP
- mypy with `check_untyped_defs` (not strict -- tool modules have broad error suppression, see `pyproject.toml` overrides)
- Pydantic v2 for models and settings
- async/await for API calls (agents use `async def chat()`)
- Rich for terminal output (panels, markdown, tables, progress spinners)
- Build system: hatchling (`pyproject.toml`)

### Known Issues (as of 2026-02-23)

- **QuickBooks** (`tools/quickbooks_mcp.py`): dead stub -- dataclass interface only, no OAuth flow, not wired into tool registry
- **SDK backend**: no session persistence (stateless per call), cost tracking logs USD but 0 tokens
