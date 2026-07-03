# CE - Agent Builder — CLAUDE.md

Project-level guidance for Claude Code sessions working on the Agent Builder (`csuite`) package.

## What this project is

The **agent factory**. Ships `SdkAgent` — the production agent class used by all Orchestration protocols in production mode — plus 89 role-scoped prompt definitions, a memory + learning shell, and three custom MCP servers (SEC EDGAR, pricing, GitHub Intel).

## Setup

```bash
cd "CE - Agent Builder"
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"                # dev tools
pip install -e ".[sdk]"                # optional: Claude Agent SDK backend
cp .env.example .env                   # set ANTHROPIC_API_KEY at minimum
```

Set `AGENT_BACKEND=sdk` in `.env` to use SdkAgent + MCP tool access. Default is `legacy` (BaseAgent + native Anthropic tool loop). See "Two backends" below.

## Quick commands

```bash
# Individual role query
csuite ceo "Should we expand into AI consulting?"

# Multi-agent synthesis
csuite synthesize "Evaluate acquiring a competitor" -a cfo cto coo

# Multi-round debate
csuite debate "Build vs. buy our data platform" -a cfo cto cmo -r 3

# Audit pipeline (7-agent sequential)
csuite audit "$12M firm, 45 employees" --revenue "$12M" --employees 45 -o audit.md

# Interactive mode: @ceo, @cfo, @all, @debate
csuite interactive

# Sessions
csuite sessions list
csuite sessions resume <id>

# Dev
pytest tests/ -m "not integration"     # CI default
pytest tests/test_foo.py -k test_name  # single test
ruff check src/ mcp_servers/
mypy src/csuite --ignore-missing-imports
streamlit run demo/app.py
```

## Architecture

### Two backends (choose one)

| Backend | Class | Tool surface | Memory / learning | Default |
|---|---|---|---|---|
| `legacy` | `BaseAgent` (`src/csuite/agents/base_agent.py`) | Native Anthropic tool loop over `csuite/tools/registry.py` (~22 tools, 939 lines) | None | Yes |
| `sdk` | `SdkAgent` (`src/csuite/agents/sdk_agent.py`) | MCP servers (Pinecone, Notion + 3 custom) | Pinecone memory + `ExperienceLog` + `PreferenceTracker` + `SelfEvaluator`/`FeedbackStore` | Set via env |

**Do not add features to both paths.** The `sdk` backend is where product investment goes. The `legacy` path is scheduled for deletion once the SDK backend is fully validated.

### SdkAgent (`src/csuite/agents/sdk_agent.py`)

- `_build_system_prompt()` composes: role prompt → memory retrieval (Pinecone) → `ExperienceLog` lessons → `PreferenceTracker` context → business context from user's `.claude/CLAUDE.md`.
- `chat(message)` streams the SDK response, captures `ToolUseBlock`/`ToolResultBlock` into `self.tool_calls` (for Langfuse tracing), records SDK-reported cost, fires `_post_response_learning` (correction detection + `SelfEvaluator` score → `FeedbackStore`).
- Not a thin wrapper — a closed-loop learning shell.

### Role registry

- `src/csuite/prompts/*_prompt.py` — 89 fat role prompts used by `SdkAgent`.
- **Prompt drift risk**: the Orchestration project holds a parallel thin registry in `protocols/agents.py`. `AgentBridge` (in Orchestration) bridges the two. Never edit a role's identity in only one place — search both trees.

### MCP servers (`mcp_servers/`)

| Server | Tools | Wraps |
|---|---|---|
| `sec_edgar_mcp` | 4 | `csuite/tools/sec_edgar.py` |
| `pricing_mcp` | 3 | `csuite/tools/pricing.py` |
| `github_intel_mcp` | 3 | `csuite/tools/github_intel.py` |

Plus Pinecone (npx) and Notion (HTTP) wired programmatically in `src/csuite/agents/mcp_config.py`.

Portable `.mcp.json` in project root — paths use `${CE_AGENT_BUILDER}` env var set by the root `.claude/settings.json`.

### Memory + learning surfaces

- `src/csuite/memory/` — Pinecone (`ce-c-suite-learning`, per-role namespaces) + DuckDB `ExperienceLog`.
- `src/csuite/learning/` — `PreferenceTracker`, `SelfEvaluator`, `FeedbackStore`.
- **Known gap**: `FeedbackStore.retrieve_exemplars()` has no non-test callers today. Closing that loop is on the roadmap (see root `RECOMMENDATION-collective-intelligence-layer.md`).

## Conventions

- **Python 3.11+**, async everywhere (`AsyncAnthropic`, `asyncio.gather`).
- **Ruff** rules E, F, I, N, W, UP; line length 100.
- **mypy** `check_untyped_defs` (not strict).
- **Pydantic v2** for models/settings.
- **Model policy**: `claude-opus-4-6` for executive reasoning, `claude-haiku-4-5-20251001` for mechanical steps.
- **Agent keys**: kebab-case (e.g. `ceo-board-prep`, `gtm-vp-sales`).
- **Tests**: `@pytest.mark.integration` on real-API tests; CI runs `-m "not integration"`.

## Files worth knowing

- `src/csuite/agents/sdk_agent.py` — the product agent
- `src/csuite/agents/base_agent.py` — legacy path (scheduled for deletion)
- `src/csuite/agents/mcp_config.py` — role→MCP-server mapping
- `src/csuite/prompts/` — 89 fat role prompts
- `src/csuite/tools/registry.py` — legacy tool registry (dead from SDK path)
- `src/csuite/orchestrator.py` — legacy multi-agent orchestrator (Orchestration project is the successor)
- `demo/app.py` — Streamlit demo UI
