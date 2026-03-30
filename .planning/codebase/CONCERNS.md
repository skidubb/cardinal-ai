# Codebase Concerns & Technical Debt

Purpose: Catalog known issues, technical debt, security risks, and architectural gaps across the CE-AGENTS monorepo. Organized by severity.

---

## Critical

### C-1. API Keys in Plaintext `.env` Files Across Three Projects

Real API keys (Anthropic, OpenAI, Google, Pinecone, Brave, xAI, Notion, government APIs) exist in plaintext `.env` files in all three sub-projects. While these files are gitignored and not tracked, they are on disk unencrypted and contain production credentials.

- `CE - Agent Builder/.env` -- 11 API keys including Anthropic, OpenAI, Pinecone, Brave, Notion, government data APIs
- `CE - Multi-Agent Orchestration/.env` -- 6 keys including Anthropic, OpenAI, Google, Pinecone, Langfuse
- `CE - Evals/.env` -- 5 keys including Anthropic, OpenAI, Google, xAI, Pinecone

Several keys are duplicated across projects with identical values, creating a wider blast radius if any single file is compromised. No secrets manager (Vault, AWS Secrets Manager, 1Password CLI) is used.

### C-2. SDK Agent Bypasses All Permission Checks

`CE - Agent Builder/src/csuite/agents/sdk_agent.py` line 264 sets `permission_mode="bypassPermissions"` when invoking Claude Agent SDK. This means SDK agents can execute any tool or MCP server operation without user confirmation, including file system writes and external API calls.

### C-3. SDK Agent Reports 0 Tokens for All Calls

`CE - Agent Builder/src/csuite/agents/sdk_agent.py` lines 307-315: cost tracking logs `input_tokens=0, output_tokens=0` because the SDK does not expose token counts. The `total_cost_usd` from the SDK is used as an override, but downstream systems that rely on token counts (cost analysis, budget alerts, Langfuse generation spans) receive incorrect data.

### C-4. Inconsistent Pricing Constants Between Projects

Two separate cost models with different prices for the same models:

- `CE - Agent Builder/src/csuite/tools/cost_tracker.py` lines 41-48: Opus at $5/$25 per MTok (labeled "February 2026")
- `CE - Multi-Agent Orchestration/protocols/cost_tracker.py` lines 27-38: Opus at $15/$75 per MTok (labeled "March 2026")

A 3x discrepancy in Opus pricing means cost comparisons between the two projects are meaningless. There is no shared pricing source of truth.

---

## Important

### I-1. QuickBooks Integration is a Dead Stub

`CE - Agent Builder/src/csuite/tools/quickbooks_mcp.py` is 324 lines of code that has never worked:
- Self-described as "stub implementation" (line 8)
- Not wired into the tool registry (`tools/registry.py`)
- OAuth token refresh sets `_token_expires = datetime.now()` (line 94), which means the "freshness" check on lines 100-102 would always trigger a re-refresh
- CFO agent configuration references QuickBooks credentials but no code path can reach this module
- Config model (`config.py` lines 47-55) validates QuickBooks fields that serve no purpose

### I-2. SDK Agent Has No Session Persistence

`CE - Agent Builder/src/csuite/agents/sdk_agent.py` line 335: `get_session_id()` returns the hardcoded string `"sdk-session"`. Unlike the legacy `BaseAgent` (which persists conversations to JSON/DuckDB), SDK agents lose all context between invocations. The agent has no conversation history, no fork/resume support, and no state continuity.

### I-3. Bare `except Exception` Swallowing Errors Throughout Orchestration

At least 40+ instances of `except Exception:` followed by `pass` or minimal logging across both projects:

- `CE - Multi-Agent Orchestration/protocols/` -- pattern in nearly every orchestrator: bare `except Exception:` around LLM calls that silently end spans with error strings but do not propagate failures. Protocols can silently produce partial results with no indication that agent calls failed.
- `CE - Agent Builder/src/csuite/learning/feedback_loop.py` -- 4 bare exception handlers (lines 100, 146, 162, 193) that swallow all errors
- `CE - Agent Builder/src/csuite/memory/store.py` -- both `store()` and `retrieve()` catch all exceptions and return False/empty list

This makes debugging production failures extremely difficult since errors are silently consumed.

### I-4. Empty Placeholder Directories

Two directories exist with no contents:
- `Shared/` -- presumably intended for shared code between projects, but empty
- `CE - Recursive Loops/` -- purpose unknown, completely empty

These create confusion about project structure and suggest abandoned or deferred work.

### I-5. Database Schema Does Not Cover Full Protocol System

`ce-db` has only 2 migrations covering 6 tables (agents, runs, agent_outputs, eval_runs, eval_samples, eval_regressions). Missing schema for:
- Protocol definitions/registry (53 protocols exist but none are modeled in the DB)
- Agent session/conversation state (SDK sessions, memory, learning logs)
- Cost tracking aggregation tables
- Langfuse trace correlation beyond a single `langfuse_trace_id` string column
- Agent tool call history (important for production debugging)

The schema was created 2026-03-04/05, only 5 days before current date, suggesting the database layer is very new and incomplete.

### I-6. No Rate Limiting on Parallel Agent Dispatch

Protocols use unbounded `asyncio.gather()` to dispatch multiple agent calls simultaneously (15+ instances found). With 56 agents in the registry and some protocols querying all agents in parallel, this can trigger Anthropic API rate limits. Only `p08_min_specs`, `p11_discovery_action_dialogue`, and `p16_ach` implement throttling via semaphore-like `_throttled()` wrappers. The retry logic in `protocols/llm.py` handles rate limit errors reactively but there is no proactive concurrency control.

### I-7. Docker Compose Uses Hardcoded Weak Credentials

`docker-compose.yml` uses `POSTGRES_PASSWORD: ce_local` and the commented-out Langfuse config shows `NEXTAUTH_SECRET: changeme-in-production`, `SALT: changeme`, `ENCRYPTION_KEY: changeme-generate-with-openssl-rand-hex-32`. Even for local dev, this creates risk if the compose file is used in any shared or deployed environment.

### I-8. Dual Agent Backend Creates Maintenance Burden

The Agent Builder maintains two complete backend implementations:
- `BaseAgent` hierarchy (7 role-specific subclasses, 706 lines in `base.py`) with session management, cost tracking, tool calling
- `SdkAgent` (335 lines in `sdk_agent.py`) with a different interface, no sessions, different cost tracking

Both must be kept in sync when adding new agents, tools, or prompts. The factory pattern (`agents/factory.py`) routes between them but the SDK backend is missing features the legacy backend has (sessions, token-level cost tracking). The legacy backend is labeled "legacy" but is still the more complete implementation.

### I-9. Production/Research Mode Default Mismatch

`CE - Multi-Agent Orchestration/protocols/agent_provider.py` line 22 defaults `_agent_mode` to `"research"`. This contradicts the MEMORY.md directive that says "ALWAYS use mode='production'". Research mode strips agents to bare dicts with no tools, no MCP servers, no memory -- producing lower quality results. If `AGENT_MODE` env var is not set and `--mode production` is not passed, runs silently use degraded agents.

### I-10. Agent Builder sys.path Manipulation for Cross-Project Import

`CE - Multi-Agent Orchestration/protocols/agent_provider.py` lines 84-87 dynamically adds `CE - Agent Builder/src` to `sys.path` at runtime using relative path resolution from the file location. This is fragile -- it breaks if the directory structure changes, if the monorepo is checked out to a different path, or if Agent Builder is installed as a proper package.

---

## Minor

### M-1. Directory Names with Spaces

All three main project directories contain spaces (`CE - Agent Builder`, `CE - Multi-Agent Orchestration`, `CE - Evals`). This requires quoting in every shell command, breaks naive path handling in scripts, and complicates CI/CD pipeline configuration. The `sys.path` manipulation in `agent_provider.py` is a direct consequence of this.

### M-2. Circuit Breaker Thresholds Are Hardcoded

`CE - Agent Builder/src/csuite/tools/resilience.py` line 19 explicitly documents this as tech debt: "Circuit breaker thresholds are hardcoded (should be configurable in Sprint 3)." The thresholds for failure counting, recovery time, and half-open state transitions cannot be tuned without code changes.

### M-3. In-Memory Only Cache in Resilience Layer

`CE - Agent Builder/src/csuite/tools/resilience.py` line 18: "In-memory cache only (no Redis/persistent cache in Sprint 2)." API response caches are lost on process restart. For CLI use this is acceptable; for long-running API server usage this wastes API calls on repeated queries.

### M-4. No Integration Tests for Multi-Agent Orchestration Protocols

The test suite in `CE - Multi-Agent Orchestration/tests/` contains mostly schema validation, smoke tests, and API endpoint tests. There are no integration tests that run actual protocols end-to-end with real LLM calls. The `test_integration_live.py` file exists but appears to be a minimal placeholder.

### M-5. DuckDB Store Silently Ignores Sequence Creation Failures

`CE - Agent Builder/src/csuite/storage/duckdb_store.py` lines 101-107: sequence creation failures are caught with `except duckdb.CatalogException: pass`. While this handles the "sequence already exists" case, it also swallows genuine catalog errors.

### M-6. Memory Store Uses Millisecond Timestamp IDs

`CE - Agent Builder/src/csuite/memory/store.py` line 45: record IDs are `f"{role}-{int(time.time() * 1000)}"`. Under high-throughput conditions (multiple rapid stores for the same role), this could produce ID collisions. A UUID-based approach would be safer.

### M-7. Feedback Loop Has No User-Facing Approval/Rejection UI

`CE - Agent Builder/src/csuite/learning/feedback_loop.py`: implements self-evaluation scoring and stores `approved: bool | None` in the `ArtifactScore` model, but there is no CLI command, API endpoint, or UI for users to actually approve or reject artifacts. The learning loop is effectively self-referential with no external signal.

### M-8. `venv_fresh` Directory Checked Into File Listing

`CE - Agent Builder/venv_fresh/` is visible in the workspace and contains a full Python 3.10 virtual environment. While likely gitignored, its presence on disk in the project root adds clutter and can confuse tools that scan for Python files (grep results include hundreds of hits from vendored pip packages).

### M-9. Streamlit Demo Uses `unsafe_allow_html=True`

`CE - Agent Builder/demo/app.py` uses `unsafe_allow_html=True` in 4 locations (lines 241, 520, 580, 672, 853). While Streamlit sandboxes HTML rendering, this pattern can enable XSS if user-provided content is rendered without sanitization.

### M-10. LLM Response JSON Parsing Has Fragile Repair Logic

`CE - Multi-Agent Orchestration/protocols/llm.py` lines 441-480: `parse_json_array()` attempts to repair truncated JSON from LLM responses by counting braces/brackets and appending closers. This heuristic fails on nested structures with string-embedded braces, escaped quotes, or multi-level truncation. The `parse_json_object()` function (lines 483-503) falls back to returning an empty dict `{}` on parse failure with no error reporting.

### M-11. Cost Tracker Pricing May Drift from Actual API Pricing

Both cost trackers use hardcoded pricing constants that must be manually updated when Anthropic changes prices. The Agent Builder tracker references "February 2026" pricing while the Orchestration tracker references "March 2026" pricing, but neither has a mechanism to verify against actual billing.
