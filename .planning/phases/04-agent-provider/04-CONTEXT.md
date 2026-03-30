# Phase 4: Agent Provider - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Production-mode SdkAgents load reliably in any environment. The API refuses to start if agent imports fail. No silent fallback to research mode. Requirements: AGNT-01, AGNT-02, AGNT-03.

</domain>

<decisions>
## Implementation Decisions

### Startup assertion (AGNT-02)
- Validate SdkAgent import in FastAPI's lifespan hook (asynccontextmanager)
- Hard crash if import fails — raise exception, uvicorn exits immediately
- Error message includes actionable fix instructions: env var path, pip editable install command
- Check depth: Claude's discretion (import-only vs smoke instantiate)

### Mode default & fallback (AGNT-03)
- Production mode is the default everywhere — API and CLI
- Never fall back to research mode silently — if production can't load, crash
- Change `_agent_mode = "research"` to `_agent_mode = "production"` in agent_provider.py
- CLI `--mode research` flag remains for explicit opt-in during local testing
- AGENT_MODE env var can override, but default constant is "production"

### Runner integration
- Replace `_resolve_agents()` in api/runner.py to use `build_production_agents()` instead of building thin dicts
- AgentBridge is already dict-compatible — orchestrators need no changes
- SdkAgent is the authoritative source — no DB enrichment (frameworks, deliverable templates, communication style) for production agents. That was a workaround for thin dicts.
- If any requested agent fails to instantiate as SdkAgent, fail the entire run with a clear error listing which agent(s) failed. No partial results from mixed production/research agents.

### Claude's Discretion
- Import mechanism approach (AGNT-01): env var (CE_AGENT_BUILDER_PATH) vs pip editable install vs hybrid
- Whether startup check does import-only or import + smoke instantiation
- How to handle the existing import_rich_agents.py and SQLite agent DB (may become dead code)
- Exact error message wording and format

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `protocols/agent_provider.py`: AgentBridge class is solid — dict-compatible wrapper around SdkAgent with chat() method. `build_production_agents()` already works, just needs path fix and fallback removal.
- `CE - Agent Builder/src/csuite/agents/sdk_agent.py`: SdkAgent class with role-based config, MCP tools, memory. The production agent implementation.
- `CE - Agent Builder/src/csuite/agents/factory.py`: Agent creation routing — determines BaseAgent vs SdkAgent.

### Established Patterns
- ce-shared `find_and_load_dotenv()` for env loading (Phase 2)
- FastAPI lifespan hook already exists in server.py for DB init — agent validation adds alongside
- `protocols/llm.py` already detects AgentBridge via `hasattr(agent, 'chat')` for production routing

### Integration Points
- `api/server.py:21-23`: lifespan hook — add SdkAgent import check here
- `api/runner.py:75-127`: `_resolve_agents()` — replace with build_production_agents() call
- `protocols/agent_provider.py:22`: `_agent_mode` default — change from "research" to "production"
- `protocols/agent_provider.py:84-87`: sys.path.insert hack — replace with env var or editable install
- `protocols/agent_provider.py:119-125`: Per-agent fallback to thin dict — remove, fail instead
- All CLI `run.py` files: `--mode` flag default changes from "research" to "production"

</code_context>

<specifics>
## Specific Ideas

- The guiding principle is "no silent degradation" — if something is broken, say so immediately and loudly
- This aligns with MEMORY.md rule: "ALWAYS use mode='production'. NEVER default to research mode."
- Error messages should be developer-friendly: what failed, why, and exactly how to fix it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-agent-provider*
*Context gathered: 2026-03-10*
