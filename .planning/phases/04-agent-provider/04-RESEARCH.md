# Phase 4: Agent Provider - Research

**Researched:** 2026-03-10
**Domain:** Python sys.path management, FastAPI lifespan, production/research agent mode switching
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Startup assertion (AGNT-02)**
- Validate SdkAgent import in FastAPI's lifespan hook (asynccontextmanager)
- Hard crash if import fails — raise exception, uvicorn exits immediately
- Error message includes actionable fix instructions: env var path, pip editable install command
- Check depth: Claude's discretion (import-only vs smoke instantiate)

**Mode default and fallback (AGNT-03)**
- Production mode is the default everywhere — API and CLI
- Never fall back to research mode silently — if production can't load, crash
- Change `_agent_mode = "research"` to `_agent_mode = "production"` in agent_provider.py
- CLI `--mode research` flag remains for explicit opt-in during local testing
- AGENT_MODE env var can override, but default constant is "production"

**Runner integration**
- Replace `_resolve_agents()` in api/runner.py to use `build_production_agents()` instead of building thin dicts
- AgentBridge is already dict-compatible — orchestrators need no changes
- SdkAgent is the authoritative source — no DB enrichment for production agents (frameworks, deliverable templates, communication style were workarounds for thin dicts)
- If any requested agent fails to instantiate as SdkAgent, fail the entire run with a clear error listing which agent(s) failed. No partial results from mixed production/research agents

### Claude's Discretion
- Import mechanism approach (AGNT-01): env var (CE_AGENT_BUILDER_PATH) vs pip editable install vs hybrid
- Whether startup check does import-only or import + smoke instantiation
- How to handle the existing import_rich_agents.py and SQLite agent DB (may become dead code)
- Exact error message wording and format

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-01 | Agent provider uses absolute path (env var) instead of fragile sys.path.insert for SdkAgent imports | Path calculation in agent_provider.py already uses `Path(__file__).resolve()` which is absolute; env var approach is the recommended extension |
| AGNT-02 | API startup asserts SdkAgent import succeeds before accepting requests — fails loudly if production mode unavailable | FastAPI lifespan hook pattern identified; existing lifespan in server.py is the insertion point |
| AGNT-03 | Production mode is the default agent mode; research mode requires explicit opt-in | `_agent_mode = "research"` in agent_provider.py line 22 is the single change point; build_agents() in agents.py already reads AGENT_MODE env var |
</phase_requirements>

---

## Summary

Phase 4 is a targeted hardening of the agent provider layer. The work is confined to four files: `protocols/agent_provider.py`, `protocols/agents.py`, `api/server.py`, and `api/runner.py`. No orchestrators, protocols, or frontend components are touched.

The current code has two problems. First, `agent_provider.py` defaults `_agent_mode = "research"`, meaning the API silently runs with thin dict agents (no tools, no memory) unless someone explicitly sets `AGENT_MODE=production`. This contradicts MEMORY.md's "ALWAYS use mode='production'" rule. Second, the path to Agent Builder's `src/` is computed via a `parents[1] / ".." / "CE - Agent Builder" / "src"` chain; while this resolves correctly today (because `__file__` is always the installed module's absolute path), it is harder to read and harder to override if the monorepo layout changes. The locked decision for AGNT-01 replaces this with an env var (`CE_AGENT_BUILDER_PATH`) that falls back to the computed path, giving operators an escape hatch without code changes.

The startup assertion (AGNT-02) slots into FastAPI's existing `lifespan` asynccontextmanager in `server.py`. The runner replacement (no part of locked decisions changes orchestrator contracts — AgentBridge is already dict-compatible via `__getitem__` and `.get()`).

**Primary recommendation:** Three discrete code changes, one new test file. Treat as a single commit.

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | installed | Lifespan hook for startup assertion | Already used |
| pytest | 9.0.2 | Test framework | Already used in tests/ |
| pathlib | stdlib | Path resolution | Already used in agent_provider.py |

### No new dependencies required.
All changes use stdlib + already-installed packages.

---

## Architecture Patterns

### Current Project Structure (relevant files only)
```
CE - Multi-Agent Orchestration/
├── api/
│   ├── server.py              # FastAPI app + lifespan — AGNT-02 insertion point
│   └── runner.py              # _resolve_agents() — AGNT-01 / AGNT-03 insertion point
├── protocols/
│   ├── agent_provider.py      # _agent_mode default + build_production_agents() — all 3 reqs
│   └── agents.py              # build_agents() — AGNT-03 default mode
└── tests/
    └── test_agent_provider.py  # Wave 0 gap — must create
```

### Pattern 1: FastAPI Lifespan Startup Assertion

**What:** The `lifespan` asynccontextmanager in `server.py` runs before the app accepts any requests. It currently only calls `create_db_and_tables()`. Adding a SdkAgent import check here means the server refuses to start (uvicorn exits with non-zero) if production mode is broken.

**When to use:** Any precondition that must hold for the entire server lifetime.

**Example:**
```python
# Source: api/server.py (existing pattern, extend it)
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # --- AGNT-02 addition ---
    try:
        from protocols.agent_provider import build_production_agents as _verify
        # import-only check; do not instantiate (avoids API key requirement at startup)
        from csuite.agents.sdk_agent import SdkAgent  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            f"Production agent import failed: {exc}\n"
            "Fix: cd 'CE - Agent Builder' && pip install -e '.[sdk]'\n"
            "Or set CE_AGENT_BUILDER_PATH=/path/to/CE - Agent Builder/src"
        ) from exc
    yield
```

**Design decision (Claude's discretion):** Use import-only check, not smoke instantiation. Instantiating SdkAgent at startup requires `ANTHROPIC_API_KEY` and MCP server connectivity. An import check verifies the code path without burning credentials or blocking startup on network I/O.

### Pattern 2: Env Var Path Override with Absolute Fallback

**What:** Replace the `parents[1] / ".." / ...` chain with a two-step resolution: check `CE_AGENT_BUILDER_PATH` env var first, fall back to the computed absolute path.

**When to use:** Any cross-project path dependency in a monorepo.

**Example:**
```python
# Source: protocols/agent_provider.py (replace lines 83-87)
import os

def _resolve_agent_builder_src() -> Path:
    env_path = os.environ.get("CE_AGENT_BUILDER_PATH")
    if env_path:
        return Path(env_path).resolve()
    # Computed fallback: __file__ is always absolute after resolve()
    return (Path(__file__).resolve().parents[2] / "CE - Agent Builder" / "src").resolve()

def build_production_agents(keys: list[str]) -> list[AgentBridge]:
    agent_builder_src = _resolve_agent_builder_src()
    if str(agent_builder_src) not in sys.path:
        sys.path.insert(0, str(agent_builder_src))
    ...
```

Note: `parents[1] / ".."` equals `parents[2]` — the refactor simplifies the path expression while keeping identical semantics when no env var is set.

### Pattern 3: Default Mode Change and Per-Agent Hard Failure

**What:** Change the module-level `_agent_mode` default from `"research"` to `"production"`. Remove the per-agent fallback to thin dict in `build_production_agents()`.

**When to use:** Any mode-gated system where silent degradation is unacceptable.

**Example:**
```python
# protocols/agent_provider.py line 22
_agent_mode: str = "production"  # was "research"

# Remove this block (lines 119-125) — replace with hard failure:
# OLD (do not keep):
#   except (ValueError, KeyError) as e:
#       agents.append(builtin)  # silent fallback

# NEW:
        except (ValueError, KeyError) as e:
            failed_agents.append(key)

    if failed_agents:
        raise RuntimeError(
            f"Failed to instantiate production agents: {failed_agents}. "
            "All agents must load as SdkAgent. "
            "Fix: verify ANTHROPIC_API_KEY and Agent Builder installation."
        )
```

### Pattern 4: Runner Replacement (_resolve_agents -> build_production_agents)

**What:** `api/runner.py`'s `_resolve_agents()` currently queries the SQLite DB for enriched dicts or falls back to the BUILTIN_AGENTS thin dict. Per the locked decision, production agents come directly from `build_production_agents()` — no DB enrichment.

**When to use:** Anywhere `_resolve_agents()` is called (single call site: `run_protocol_stream` and `run_pipeline_stream`).

**Example:**
```python
# api/runner.py — replace _resolve_agents() call
from protocols.agent_provider import build_production_agents

# In run_protocol_stream and run_pipeline_stream, replace:
#   agents = _resolve_agents(agent_keys)
# with:
    agents = build_production_agents(agent_keys)
```

The `_resolve_agents()` function itself can be deleted or kept for reference. `import_rich_agents.py` and the SQLite agent DB become read-only reference data (they are not removed in this phase — they may be removed in a later cleanup phase per Claude's discretion).

### Anti-Patterns to Avoid

- **Silent fallback to research mode:** The entire value of this phase is removing the silent degradation path. Any `except` clause that substitutes a thin dict for a failed SdkAgent is wrong.
- **Smoke instantiation at startup:** Calling `SdkAgent(role="ceo")` in the lifespan hook requires API keys and MCP connectivity to be present at startup time. An import-only check is sufficient to verify the code path exists.
- **Changing orchestrators:** AgentBridge already implements `__getitem__`, `.get()`, and `.chat()`. No orchestrator protocol code needs to change.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path resolution | Custom string manipulation for paths | `pathlib.Path(__file__).resolve().parents[N]` | stdlib; `resolve()` always returns absolute path |
| Import verification | subprocess, importlib tricks | Direct `from csuite.agents.sdk_agent import SdkAgent` in try/except | Simplest; catches all ImportError variants |
| Startup gating | Custom request middleware | FastAPI `lifespan` asynccontextmanager | Already the pattern in server.py; uvicorn respects exceptions from lifespan |

---

## Common Pitfalls

### Pitfall 1: Forgetting AGENT_MODE Env Override in build_agents()

**What goes wrong:** `protocols/agents.py:build_agents()` reads `os.environ.get("AGENT_MODE", "production")`. If a caller passes `mode=None` explicitly, it reads the env var. But if someone sets `AGENT_MODE=research` in their shell, all CLI runs silently use research mode even after the default constant changes.

**Why it happens:** The env var override is intentional for explicit opt-out, but it can mask problems in CI/CD environments where `AGENT_MODE` is set.

**How to avoid:** The default constant change in `agent_provider.py` is the source of truth. The env var is documented as explicit opt-out only. No code change needed — just document this in error messages.

### Pitfall 2: SdkAgent Init Requires ANTHROPIC_API_KEY

**What goes wrong:** If the startup check instantiates `SdkAgent(role="ceo")`, it calls `get_settings()` which reads `ANTHROPIC_API_KEY`. In Docker or CI environments, the key may not be available at container start.

**Why it happens:** `SdkAgent.__init__` calls into `csuite.config.get_agent_config()` and `get_settings()`.

**How to avoid:** Import-only check. `from csuite.agents.sdk_agent import SdkAgent` verifies the module is importable without instantiation.

### Pitfall 3: sys.path Pollution Across Test Runs

**What goes wrong:** `sys.path.insert(0, str(agent_builder_src))` in `build_production_agents()` persists across test runs in the same pytest session. If Agent Builder's `src/` shadows an orchestration module name, imports in later tests may resolve incorrectly.

**Why it happens:** `sys.path` is global and shared within a Python process.

**How to avoid:** The env var approach (`CE_AGENT_BUILDER_PATH`) doesn't change this — `sys.path.insert()` remains. The guard `if str(agent_builder_src) not in sys.path` prevents duplicate insertion. This is acceptable for the current monorepo layout. A future improvement would be to install Agent Builder as an editable package instead.

### Pitfall 4: _resolve_agents() Still Called from Pipeline Runner

**What goes wrong:** `run_protocol_stream` and `run_pipeline_stream` both call `_resolve_agents()`. If only one call site is updated, half the runs use thin dicts.

**Why it happens:** Two separate functions in `runner.py` both build the agent list.

**How to avoid:** Search for all calls to `_resolve_agents()` before committing. There are exactly two (lines ~222 and ~548 in runner.py).

---

## Code Examples

Verified patterns from source inspection:

### Existing Lifespan Hook (extend, do not replace)
```python
# Source: CE - Multi-Agent Orchestration/api/server.py:20-23
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
```

### Existing Path Computation (current form, lines 83-87)
```python
# Source: CE - Multi-Agent Orchestration/protocols/agent_provider.py:83-87
agent_builder_src = Path(__file__).resolve().parents[1] / ".." / "CE - Agent Builder" / "src"
agent_builder_src = agent_builder_src.resolve()
if str(agent_builder_src) not in sys.path:
    sys.path.insert(0, str(agent_builder_src))
```

Note: `parents[1] / ".."` is mathematically equivalent to `parents[2]`. The refactor simplifies this while adding env var override.

### Existing Per-Agent Fallback (remove this block entirely, lines 119-125)
```python
# Source: CE - Multi-Agent Orchestration/protocols/agent_provider.py:119-125
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to create production agent '%s': %s. "
                "Falling back to research mode for this agent.", key, e
            )
            agents.append(builtin)  # type: ignore[arg-type]
```

### Existing _resolve_agents call sites (both must change)
```python
# Source: api/runner.py:222 (run_protocol_stream)
agents = _resolve_agents(agent_keys)

# Source: api/runner.py:548 (run_pipeline_stream)
agents = _resolve_agents(agent_keys)
```

### Existing build_agents() mode resolution (agents.py:421)
```python
# Source: CE - Multi-Agent Orchestration/protocols/agents.py:421
mode = mode or os.environ.get("AGENT_MODE", "production")
```
This already defaults to "production" in `build_agents()`. The fix in `agent_provider.py` makes the module-level constant consistent with this.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Research mode default | Production mode default | This phase | Silent degradation eliminated |
| sys.path hack (fragile) | env var + computed fallback | This phase | Operators can override without code change |
| Per-agent fallback to thin dict | Hard failure on agent instantiation | This phase | Partial-production runs eliminated |
| DB-enriched thin dicts in runner | build_production_agents() | This phase | SdkAgent is authoritative, DB enrichment code becomes dead path |

**Deprecated/outdated after this phase:**
- `_resolve_agents()` in runner.py: replaced by `build_production_agents()`. Can be deleted in a cleanup phase.
- SQLite agent DB enrichment fields (frameworks_json, deliverable_template, communication_style): no longer used for protocol runs. The DB and `import_rich_agents.py` remain but are not called by the runner.

---

## Open Questions

1. **Should `import_rich_agents.py` and the SQLite DB become dead code in this phase?**
   - What we know: The locked decision says "SdkAgent is the authoritative source — no DB enrichment." The runner no longer calls `_resolve_agents()` which reads the DB.
   - What's unclear: The `/api/agents/import-rich` route still exists and calls `import_rich_agents()`. The DB still stores agent records created via the API.
   - Recommendation: Leave `import_rich_agents.py` and the DB intact in this phase. They are not in scope per "deferred: none — discussion stayed within phase scope." A subsequent cleanup phase can remove them if needed.

2. **Should `CE_AGENT_BUILDER_PATH` be documented in `.env.example`?**
   - What we know: The env var is only needed when the monorepo layout changes from the expected sibling-directory structure.
   - Recommendation: Add a commented-out entry in `.env.example` with a note that it defaults to the sibling directory. Low-cost documentation.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none — no pytest.ini or pyproject.toml detected |
| Quick run command | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && python -m pytest tests/test_agent_provider.py -x` |
| Full suite command | `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate && python -m pytest tests/ -m "not integration" -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-01 | Path resolves correctly regardless of CWD | unit | `python -m pytest tests/test_agent_provider.py::test_path_resolution -x` | Wave 0 gap |
| AGNT-01 | CE_AGENT_BUILDER_PATH env var overrides computed path | unit | `python -m pytest tests/test_agent_provider.py::test_env_var_override -x` | Wave 0 gap |
| AGNT-02 | Server startup fails if SdkAgent import fails | unit | `python -m pytest tests/test_agent_provider.py::test_startup_assertion_fails -x` | Wave 0 gap |
| AGNT-02 | Server starts normally when SdkAgent is importable | unit | `python -m pytest tests/test_agent_provider.py::test_startup_assertion_passes -x` | Wave 0 gap |
| AGNT-03 | Default agent mode is "production" | unit | `python -m pytest tests/test_agent_provider.py::test_default_mode_is_production -x` | Wave 0 gap |
| AGNT-03 | AGENT_MODE=research env var enables research mode | unit | `python -m pytest tests/test_agent_provider.py::test_research_mode_opt_in -x` | Wave 0 gap |
| AGNT-03 | build_production_agents raises RuntimeError if any agent fails | unit | `python -m pytest tests/test_agent_provider.py::test_hard_failure_on_agent_failure -x` | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_agent_provider.py -x`
- **Per wave merge:** `python -m pytest tests/ -m "not integration" -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_agent_provider.py` — covers AGNT-01, AGNT-02, AGNT-03 with mocked SdkAgent imports
- [ ] No pytest.ini or conftest.py needed — existing test infrastructure (no markers required for unit tests)

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `CE - Multi-Agent Orchestration/protocols/agent_provider.py` — full file read, path computation and mode default verified
- Direct code inspection: `CE - Multi-Agent Orchestration/api/server.py` — lifespan hook structure verified
- Direct code inspection: `CE - Multi-Agent Orchestration/api/runner.py` — both `_resolve_agents()` call sites located (lines ~222 and ~548)
- Direct code inspection: `CE - Multi-Agent Orchestration/protocols/agents.py` — `build_agents()` mode default logic verified
- Direct code inspection: `CE - Multi-Agent Orchestration/protocols/llm.py` — `hasattr(agent, "chat")` production detection confirmed
- Direct code inspection: `CE - Agent Builder/src/csuite/agents/sdk_agent.py` — SdkAgent init requirements verified

### Secondary (MEDIUM confidence)
- Git history: `f8c739a` — CONTEXT.md locked decisions extracted verbatim
- CLAUDE.md (orchestration): Agent mode documentation, production/research mode semantics
- MEMORY.md: "ALWAYS use mode='production'" rule confirmed

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code read directly from source
- Architecture: HIGH — all insertion points identified by line number
- Pitfalls: HIGH — derived from direct reading of the fallback code that must be removed
- Test gaps: HIGH — no test_agent_provider.py exists; confirmed by directory listing

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable codebase — no external dependencies changing)
