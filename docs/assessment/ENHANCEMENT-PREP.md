# Enhancement Prep — Cardinal Element Agentic Platform

**Status:** Build-prep reference. Each section is ready to implement — no design decisions pending.
**Branch:** `claude/add-rc-config-support-W9iw7` (Railway production)
**Date:** 2026-06-11

---

## 1. Caching & Resilience *(Tier 1 — in progress)*

### Current state

- `protocols/llm.py` — `llm_complete()` and `agent_complete()` dispatch all Anthropic calls. Token usage including `cache_read_input_tokens` is already extracted at line 157; `ce_shared.pricing` already carries cache multipliers (`write_multiplier=1.25`, `read_multiplier=0.1`).
- `protocols/server_agent.py` — chat loop (lines 324–406) sends `messages.create()` with raw system + tools payload on every turn; no cache breakpoint annotation.
- `protocols/agent_provider.py` — `build_production_agents()` re-imports Agent Builder prompt/tool-map on every call via `ServerAgent.__init__`.
- `api/tool_executor.py` — `execute_tool()` has no per-tool timeout; a slow external API (Census, BLS, GitHub) blocks the entire tool loop indefinitely.
- `api/runner.py` — SSE stream has no partial-failure event type; a single failing agent silently drops.
- No router memoization exists in `api/routers/router.py`.

### Design

**Anthropic prompt caching.** Add `cache_control: {"type": "ephemeral"}` to the last system-message block in every `messages.create()` call. Render order is tools → system → messages; the cache breakpoint must sit at the boundary between the static prefix (tools + system prompt) and the volatile suffix (institutional memory, question). Minimum cacheable prefix: 4096 tokens for Opus/Haiku-4.5, 2048 for Sonnet-4.6 — small Haiku orchestration prompts may not cache, which is acceptable. Track savings via `usage.cache_read_input_tokens` already extracted in `_record_usage()`.

**Router memoization.** TTL dict in `api/routers/router.py` keyed by `sha256(question + sorted_agents)`. Default TTL 300 s. Only applies to the `/api/router/decide` path.

**Agent-resolution caching.** Module-level `functools.lru_cache` on the Agent Builder prompt + tool-map import call inside `build_production_agents()` in `protocols/agent_provider.py`. Keys: agent key string. Invalidate on server restart only (prompts are stable per deploy).

**Per-tool timeout + circuit breaker.** In `api/tool_executor.py`: wrap `execute_tool()` with `asyncio.wait_for(coro, timeout=60.0)`; raise `ToolTimeoutError` on expiry. Circuit breaker: module-level `dict[str, _ToolBreakerState]` tracking consecutive failures per tool name; open after 5 failures, half-open after 30 s. Surface partial failures as `{"event": "tool_warning", "tool_name": ..., "reason": "timeout|circuit_open"}` SSE events from `api/runner.py`.

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/protocols/server_agent.py` | Add `cache_control` block to `create_kwargs` system entry (lines 280–324 region) |
| `CE - Multi-Agent Orchestration/protocols/llm.py` | Same for `llm_complete()` + `agent_complete()` Anthropic paths |
| `CE - Multi-Agent Orchestration/protocols/agent_provider.py` | `lru_cache` on prompt/tool-map import calls in `build_production_agents()` |
| `CE - Multi-Agent Orchestration/api/routers/router.py` | TTL dict memoization on `/decide` path |
| `CE - Multi-Agent Orchestration/api/tool_executor.py` | `asyncio.wait_for` wrapper + `_ToolBreakerState` circuit breaker dict |
| `CE - Multi-Agent Orchestration/api/runner.py` | Emit `tool_warning` SSE events on `ToolTimeoutError` / circuit open |

### Effort: S

### Dependencies

None — no new tables, no new packages. `asyncio` and `functools.lru_cache` are stdlib.

### Acceptance criteria

1. A second identical `/api/router/decide` call within 300 s returns in < 50 ms (memoized).
2. `usage.cache_read_input_tokens > 0` on the second call to any Opus protocol run (verifiable in Langfuse or cost tracker log).
3. A tool call that hangs > 60 s surfaces a `tool_warning` SSE event and the run continues rather than blocking.
4. Five consecutive tool failures trip the circuit breaker; call 6 returns `tool_warning` without attempting the external API.

---

## 2. Tool-Call Optimization *(Tier 2)*

### Current state

- `protocols/server_agent.py` lines 335–406: the tool loop iterates over `response.content` blocks sequentially with `await _execute_tool(...)` per block. Claude can and does emit multiple `tool_use` blocks in a single response; they are executed one at a time.
- `protocols/server_agent.py` receives no hint about which tools are relevant to the current protocol stage.
- No memoization of tool results within a run — the same `brave_search("market size")` call fires twice if two agents ask the same question.

### Design

**Parallel tool execution.** Replace the sequential `for block in response.content` loop with `asyncio.gather(*[_execute_tool(b.name, b.input) for b in tool_blocks])`. Results must be mapped back to their originating `tool_use_id` (Claude requires result ordering by `tool_use_id`). Use `zip(tool_blocks, results)` after gather.

**Per-stage tool pruning.** Add an optional `tools_subset: list[str]` field to `capability.yaml` stages (only protocols with multi-stage flows need this). `ServerAgent.chat()` accepts an optional `allowed_tools: list[str]` kwarg; if provided, filter `ALL_TOOL_SCHEMAS` before building `create_kwargs`. Example: the ACH (p16) evidence-collection stage only needs `brave_search` + `sec_edgar`; the hypothesis-rating stage needs nothing.

**Per-run tool-result memoization.** Module-level `dict` keyed by `(tool_name, canonical_json(args))` attached to the `run_protocol_stream` context (or passed as a shared cache object into `ServerAgent`). Before calling `_execute_tool`, check cache; on miss, populate after call. TTL: run lifetime (clear on run completion). This is especially effective for multi-agent protocols where several agents call `brave_search` with the same query.

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/protocols/server_agent.py` | Parallel gather in tool loop (lines 338–391); accept `allowed_tools` kwarg |
| `CE - Multi-Agent Orchestration/api/tool_executor.py` | Add `run_tool_cache: dict | None` param to `execute_tool()`; check before dispatch |
| `CE - Multi-Agent Orchestration/protocols/p{NN}_{name}/capability.yaml` | Add `tools_subset` to relevant stage definitions (start with p16, p06, p32) |
| `CE - Multi-Agent Orchestration/api/runner.py` | Instantiate shared tool cache dict per run; pass into agent calls |

### Effort: M

### Dependencies

Enhancement 1 (circuit breaker + timeout) should land first so parallel tool gather does not amplify timeout storms.

### Acceptance criteria

1. A P03 parallel synthesis run with 3 agents each calling `brave_search` on the same query issues 1 network call, not 3.
2. A response with 2 simultaneous `tool_use` blocks resolves in `max(t1, t2)` elapsed time, not `t1 + t2`.
3. A P16 ACH evidence-collection stage only sends `brave_search` and `sec_edgar` schemas to Claude (verifiable via request inspection or log).

---

## 3. Blackboard Generalization *(Tier 2)*

### Current state

- `protocols/blackboard.py` — `Blackboard` class is an in-memory, append-only store with topic/author/stage scoping and watcher callbacks. Currently only P54 (Blackboard protocol) instantiates it directly.
- Blackboard entries hold arbitrary `content: Any`; orchestrators parse these via ad-hoc string matching, which is fragile.
- No Postgres persistence; a Railway restart loses all in-flight blackboard state.
- Context assembly (`protocols/context_assembler.py`) runs once before the protocol starts (see `api/runner.py` lines 264–275); agents do not get mid-run graph reads.

### Design

**Opt-in SharedState service.** Expose `protocols/blackboard.py:Blackboard` as a mountable service: `orchestrator.__init__` accepts an optional `blackboard: Blackboard | None = None`. If provided, orchestrator calls `blackboard.write(topic, content, author, stage)` after each stage and `blackboard.snapshot(visible_to=role)` before each agent call. Any protocol can opt in by passing a `Blackboard` instance from the runner.

**Structured outputs for contributions.** Where protocols collect structured contributions (hypotheses, evidence, scores), replace free-text parsing with a typed Pydantic model + `response_format` / `output_config: {format: json_schema, schema: ...}` in `llm_complete()`. The schema is defined once in `prompts.py` and imported into the orchestrator. Start with P16 ACH and P54 Blackboard.

**Postgres-backed durable entries.** New `BlackboardEntry` SQLModel table: `id, run_id, tenant_slug, topic, author, stage, content_json, version, created_at`. Add migration in `ce-db`. On every `blackboard.write()`, persist to Postgres async (best-effort, same try/except pattern as `graph_writer.py`). On pipeline resume, re-hydrate from DB into a fresh `Blackboard` instance.

**Mid-run graph reads.** In `api/runner.py`, after each stage SSE event fires, call `context_assembler.assemble_context(tenant_slug, stage_output[:500], agent_keys)` and append the delta to agents' `institutional_memory`. Gate behind a `mid_run_graph_reads: bool` flag on the run request (default False; too slow for every stage until latency is profiled).

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/protocols/blackboard.py` | Add `async write_pg()`, `snapshot()` method; accept `db_session` param |
| `CE - Multi-Agent Orchestration/api/runner.py` | Instantiate `Blackboard` per run when `enable_blackboard=True`; mid-run context hook |
| `CE - Multi-Agent Orchestration/api/models.py` | New `BlackboardEntry` SQLModel table |
| `ce-db/` alembic migrations | Migration for `blackboard_entry` table |
| `protocols/p16_ach/orchestrator.py` | Switch contribution parsing to Pydantic schema + json_schema output |
| `protocols/p54_blackboard/orchestrator.py` | Mount shared `Blackboard` instance; use `snapshot()` before each agent call |

### Effort: M

### Dependencies

Requires `ce-db` Alembic migration access and Railway Postgres. No new packages.

### Acceptance criteria

1. A P54 run resumed after a Railway restart re-hydrates its blackboard from Postgres and continues from the last completed stage.
2. P16 ACH `hypothesis_rating` stage returns a typed JSON object matching the declared schema, with no string parsing needed.
3. Any protocol that opts in via `blackboard=Blackboard(...)` sees its per-stage writes appear in `GET /api/runs/{id}` output.

---

## 4. Router Enhancements *(Tier 2)*

### Current state

- `protocols/adaptive_router/resolver.py` lines 26–41: `DEFAULT_ALLOWLIST` is a hard-coded `frozenset` of 12 protocol keys. Adding a new protocol requires a code change.
- `protocols/registry.py:build_routing_prompt_section()` generates the P0a routing prompt from `capability.yaml` cost tiers and problem types; it does not include historical performance data.
- `api/routers/router.py` does not expose a pre-run cost estimate.
- The portal `RunForm` has no cost estimate before submission.

### Design

**Capability-driven eligibility.** Add a `routable: bool` field (default `true`) to each `capability.yaml`. Modify `protocols/adaptive_router/resolver.py:_load_manifest()` to build the allowlist dynamically from all protocols with `routable: true` rather than from `DEFAULT_ALLOWLIST`. Static allowlist becomes the fallback if no yaml is found. Update `ProtocolCapability` dataclass in `protocols/registry.py` to carry `routable`.

**Outcome-fed routing prompt.** Extend `build_routing_prompt_section()` to accept an optional `db_session` and query `SELECT protocol_key, AVG(judge_verdict_json->>'overall'), COUNT(*) FROM run WHERE status='completed' AND tenant_slug=$1 GROUP BY protocol_key`. Append a "Protocol performance" block to the P0a system prompt. Skip gracefully if DB unavailable or no data.

**Cost-estimate endpoint.** `POST /api/router/estimate` — accepts same payload as `/run`; calls `orchestrator.decide()`, reads `cost_tier` from resolver result, looks up token estimates from `ce_shared.pricing.MODEL_PRICING`, returns `{protocol_key, estimated_cost_usd_low, estimated_cost_usd_high, cost_tier}`. No LLM call other than the router decision itself.

**Portal integration.** Wire `RunForm` to call `/api/router/estimate` on question change (debounced 800 ms) and display cost range badge before the submit button.

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/protocols/adaptive_router/resolver.py` | Dynamic allowlist from yaml `routable` field; keep static fallback |
| `CE - Multi-Agent Orchestration/protocols/registry.py` | Add `routable` to `ProtocolCapability`; extend `build_routing_prompt_section()` with perf data |
| `CE - Multi-Agent Orchestration/api/routers/router.py` | Add `POST /estimate` endpoint |
| `CE - Multi-Agent Orchestration/protocols/p*/capability.yaml` | Add `routable: true` (or `false` for experimental protocols) |
| `cardinal-portal/` RunForm component | Cost estimate badge with debounced API call |

### Effort: M

### Dependencies

`ce_shared.pricing.MODEL_PRICING` must carry Opus-4.7 + Haiku-4.5 pricing (verify current; update if needed). Portal change requires Next.js env var pointing to Railway API.

### Acceptance criteria

1. A new protocol with `routable: true` in `capability.yaml` becomes eligible for routing without a code change to `resolver.py`.
2. A protocol with `routable: false` is never selected by the router even if P0a recommends it.
3. `POST /api/router/estimate` returns within 3 s and includes `estimated_cost_usd_low` and `estimated_cost_usd_high`.
4. Portal RunForm displays the estimate badge before run submission.

---

## 5. Automated Orchestration *(Tier 2)*

### Current state

- `api/routers/pipelines.py` — `POST /api/pipelines/run` executes a fixed step list; `POST /api/pipelines/resume/{run_id}` exists but replay from `Run.steps_json` is incomplete (no step-output replay; resumes from step 0).
- Pipeline steps have no conditional branching (`PipelineStep` model in `api/models.py` has no `condition` field).
- No auto-composition endpoint.

### Design

**Conditional pipeline steps.** Add `condition: str | None` to `PipelineStep` SQLModel (and to the `steps_json` schema). The runner evaluates `condition` as a simple Python expression with `confidence`, `cost_usd`, and `prev_output` in scope. Example: `"confidence < 50"` → escalate to a heavier protocol. Evaluator: `eval(condition, {"confidence": ..., "cost_usd": ..., "prev_output": ...})` behind a whitelist of allowed names.

**Pipeline resume.** On `POST /api/pipelines/resume/{run_id}`: load `Run.steps_json` and `RunStep` rows; find the last `RunStep` with `status='completed'`; pass its `output_text` as the context injection for the next step. Do not re-run completed steps.

**Auto-composition endpoint.** `POST /api/router/compose` — accepts `{question, agents, max_steps: int = 3, max_cost_tier: str}`. Calls router `/decide` for step 1. If the decision confidence is high: return a 1-step pipeline. If medium: call Haiku with a chain-selection prompt (from `protocols/registry.py` capability descriptions) to suggest 1–2 follow-on protocols. Return `{pipeline: [{protocol_key, rationale}], total_estimated_cost}`.

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/api/models.py` | Add `condition: str | None` to `PipelineStep` |
| `CE - Multi-Agent Orchestration/api/routers/pipelines.py` | Condition evaluator in step execution loop; resume logic fix |
| `CE - Multi-Agent Orchestration/api/runner.py` | `run_pipeline_stream()`: skip completed `RunStep` rows, inject prior output |
| `CE - Multi-Agent Orchestration/api/routers/router.py` | `POST /api/router/compose` endpoint |

### Effort: M

### Dependencies

Enhancement 4 (router enhancements) must land first so `/compose` can call `/decide` internally.

### Acceptance criteria

1. A pipeline with `condition: "confidence < 50"` on step 2 skips that step when step 1 router confidence is ≥ 50.
2. `POST /api/pipelines/resume/{run_id}` continues from the last completed `RunStep` without re-running earlier steps.
3. `POST /api/router/compose` returns a 1–3 step pipeline with per-step rationale in < 5 s.

---

## 6. Automated Agent Creation *(Tier 4)*

### Current state

- `api/routers/agents.py` — full CRUD for the `Agent` SQLModel table: create, read, update, delete. The `Agent` model (`api/models.py` lines 15–36) already carries `system_prompt`, `tools_json`, `model`, `temperature`, `personality`, `frameworks_json`.
- `CE - Agent Builder/src/csuite/agents/sdk_agent.py` — `_ROLE_PROMPTS` dict with 80 pre-built role system prompts; `CE - Agent Builder/src/csuite/tools/schemas.py` — `ALL_TOOL_SCHEMAS` with 27 tool definitions.
- `CE - Evals/src/ce_evals/core/runner.py` — `EvalRunner` for running blind-judge evaluations.
- No endpoint generates an agent from a role description.

### Design

**`POST /api/agents/generate`.** Accepts `{role_description: str, tenant_slug}`. Calls Opus with a meta-prompt to: (a) write a system prompt for the role; (b) select the 3–5 most semantically relevant tool names from `ALL_TOOL_SCHEMAS` (pass tool descriptions, not full schemas). Returns a draft `Agent` dict with `is_builtin=False` and `status='pending_eval'`.

**CE-Evals smoke gate.** After generation: run `EvalRunner` with `BlindJudge` on 3 canned questions against the new agent and the 2 nearest existing agents (cosine similarity of system prompt embeddings against `_ROLE_PROMPTS`). If the new agent scores within 1 point of the nearest existing agent on all 3 questions, activate (`status='active'`). Otherwise, return the draft with `eval_report` for human review.

**Portal wizard.** New route `/agents/new` in the portal: multi-step form (role name → description → preview generated prompt → eval results → activate/discard).

**A/B harness.** On activation, the portal can flag `ab_test=True` on the custom agent. When the router selects an agent key that matches both a builtin and a custom agent, randomly split 50/50. Log both outcomes to `AgentOutput`. After 20 runs, promote the winner.

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/api/routers/agents.py` | Add `POST /api/agents/generate` endpoint |
| `CE - Multi-Agent Orchestration/api/models.py` | Add `status: str` (pending_eval/active/archived) and `eval_report_json: str` to `Agent` |
| `CE - Evals/src/ce_evals/core/runner.py` | Expose `run_smoke_test(agent, questions, judges)` helper |
| `cardinal-portal/` | `/agents/new` wizard pages |

### Effort: L

### Dependencies

Enhancement 9 (CI eval gate) should be in place first to establish eval infrastructure. Requires Pinecone for system-prompt embedding similarity (existing `PINECONE_API_KEY`).

### Acceptance criteria

1. `POST /api/agents/generate` returns a draft agent with system prompt and tool list in < 30 s.
2. A generated agent scoring within 1 point of its nearest existing agent on all 3 smoke questions is auto-activated.
3. A generated agent scoring below threshold is returned as a draft with `eval_report` and is not callable in protocol runs.

---

## 7. Knowledge Optimization *(Tier 3)*

### Current state

- `CE - Agent Builder/src/csuite/memory/store.py` — `MemoryStore.store()` upserts to Pinecone with no dedup check; duplicate records accumulate for the same insight stored multiple times.
- `MemoryStore.retrieve()` ranks by semantic similarity only; no recency weighting.
- No expiry policy for stale `fact` memories.
- `protocols/graph_writer.py` — `write_decision()` writes a `Decision` node after each run; judge verdict score is extracted via `_extract_eval_score()` but is not stored as a graph property on the node (only logged).
- Connector sync cadence is manual (no scheduled re-sync).

### Design

**Pinecone dedup on upsert.** Before `index.upsert_records()`, call `index.query(vector=embed(content), top_k=1, namespace=role)`. If top result `score > 0.95`, skip the upsert (or merge by appending a timestamp tag to the existing record). Adds one query per store call — acceptable given store() is called asynchronously post-run.

**Recency decay at retrieval.** After `index.search_records()` returns results, re-score: `final_score = similarity_score × exp(-age_days / half_life)` where `half_life=90` (configurable via env var `MEMORY_HALF_LIFE_DAYS`). Sort by `final_score` before returning top-k.

**Expiry policy.** Scheduled task (see Enhancement 8 for APScheduler setup): daily query Pinecone for all records in each role namespace with `memory_type=fact` and `timestamp < now - expiry_days`. Delete expired records. `expiry_days` default 180, configurable per tenant via `tenant.yaml`.

**Judge score on graph Decision node.** In `protocols/graph_writer.py:write_decision()`, include `eval_score` as a property on the `Decision` node when `envelope.judge_verdict` is present. In `protocols/context_assembler.py`, prefer `Decision` nodes with `eval_score > 7.0` in the retrieval query (Cypher `ORDER BY d.eval_score DESC`).

**Connector sync cadence.** Add a `sync_cadence_cron` field to the `Integration` SQLModel (`api/models.py`). When the APScheduler from Enhancement 8 is live, register a job per enabled integration at the specified cron expression to re-trigger the ingest pipeline.

### Files to modify

| File | Change |
|------|--------|
| `CE - Agent Builder/src/csuite/memory/store.py` | Dedup query before upsert; recency decay in `retrieve()` |
| `CE - Multi-Agent Orchestration/protocols/graph_writer.py` | Write `eval_score` property on Decision node |
| `CE - Multi-Agent Orchestration/protocols/context_assembler.py` | Score-weighted Cypher query for Decision retrieval |
| `CE - Multi-Agent Orchestration/api/models.py` | Add `sync_cadence_cron: str` to `Integration` |

### Effort: M

### Dependencies

Enhancement 8 (APScheduler in FastAPI) is needed for the expiry sweep and connector re-sync. Dedup and recency decay are standalone.

### Acceptance criteria

1. Storing the same memory content twice in a 60-second window results in 1 Pinecone record, not 2.
2. A 2-year-old `fact` memory scores lower than a 30-day-old record on the same query with identical similarity.
3. `write_decision()` writes `eval_score` to the graph node when judge verdict is present; `context_assembler` returns high-scoring decisions first.

---

## 8. Recurring Research *(Tier 3)*

### Current state

- No standing-question concept exists anywhere in the codebase.
- `api/server.py` has no scheduler in its FastAPI lifespan.
- `api/runner.py:run_protocol_stream()` is the sole run entrypoint and is SSE-only; no batch/headless invocation path.
- `protocols/graph_writer.py` writes `Decision` nodes; no `Lesson` node for diff-based insights.

### Design

**`StandingQuestion` table.** New SQLModel: `id, tenant_slug, question, pipeline_ref (JSON step list), cadence_cron, last_run_id, last_run_at, notify_email, created_at`. Add via Alembic migration in `ce-db`.

**APScheduler in FastAPI lifespan.** In `api/server.py` FastAPI lifespan context: instantiate `AsyncIOScheduler` (APScheduler 3.x, already available or add to `requirements.txt`). On startup, load all `StandingQuestion` rows and register a cron job per row. Railway runs a single instance (no distributed lock needed). Add `POST /api/research`, `GET /api/research`, `PUT /api/research/{id}`, `DELETE /api/research/{id}` endpoints in new `api/routers/research.py`.

**Headless run path.** Add `run_protocol_headless(protocol_key, question, agent_keys, tenant_slug, ...)` to `api/runner.py` — same logic as `run_protocol_stream()` but no SSE generator; returns the final `RunEnvelope` directly. The scheduler calls this path.

**Diff + delta write.** After a scheduled run completes: (a) load the previous run's `result_summary` for the same `StandingQuestion`; (b) call Haiku with a diff prompt to produce a 3-bullet change summary; (c) write the delta as a `Lesson` node in ce-graph linked to both the prior `Decision` and the new `Decision`; (d) if `notify_email` is set, send via Railway-configured SMTP or Resend API.

**Portal `/research` page.** List standing questions with last-run status, next scheduled run, and delta timeline (accordion of Lesson node diffs per run).

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/api/server.py` | APScheduler in lifespan; job registration from DB on startup |
| `CE - Multi-Agent Orchestration/api/models.py` | `StandingQuestion` SQLModel table |
| `CE - Multi-Agent Orchestration/api/runner.py` | `run_protocol_headless()` |
| `CE - Multi-Agent Orchestration/api/routers/research.py` | New router: CRUD for standing questions |
| `CE - Multi-Agent Orchestration/protocols/graph_writer.py` | `write_lesson()` with diff summary and link to prior `Decision` |
| `ce-db/` alembic | Migration for `standing_question` table |
| `cardinal-portal/` | `/research` page with standing question CRUD + delta timeline |

### Effort: L

### Dependencies

Enhancement 5 (pipeline resume) must be complete — standing questions reference pipeline definitions. Enhancement 7 (graph Decision score) should be complete so delta writes can reference scored decisions.

### Acceptance criteria

1. A `StandingQuestion` with `cadence_cron="0 8 * * 1"` fires every Monday at 08:00 UTC and creates a new `Run` row.
2. The second scheduled run produces a Haiku diff summary stored as a `Lesson` node in ce-graph.
3. `GET /api/research/{id}` returns the question, last run ID, and the last diff summary.
4. Portal `/research` page renders the standing question list and delta timeline without a full page reload.

---

## 9. Usability & Market Utility *(Tier 4)*

### Current state

- `api/models.py:Run` — `error_message: Optional[str]` stores raw exception text. No structured error taxonomy.
- `api/routers/usage.py` — `GET /api/usage` aggregates by status; no budget alert mechanism.
- No `/admin` or `/billing` routes exist in the portal.
- CI runs `pytest -m "not integration"` but has no eval regression gate.
- No first-customer onboarding document.

### Design

**Error-code taxonomy.** Define `class RunErrorCode(str, Enum)` in `api/models.py`: `TIMEOUT`, `TOOL_FAILURE`, `LLM_ERROR`, `AUTH`, `QUOTA`, `CONTEXT`. Add `error_code: Optional[str]` column to `Run`. In `api/runner.py` exception handlers, map exception types to enum values before writing `Run.status='failed'`. Emit `{"event": "error", "error_code": "TIMEOUT", "message": "..."}` as the terminal SSE event. Portal RunDetail page renders a human-readable error card with a suggested action per code.

**Pre-run cost estimate + budget alerts.** Extend `GET /api/usage` to include `monthly_budget_usd` (stored in a new `TenantConfig` table keyed by `tenant_slug`). Add `POST /api/usage/budget` to set the budget. When a run completes and `sum(cost_usd) WHERE month=current AND tenant_slug=X` crosses 80% and 100% of budget, write a `budget_alert` event to a `notifications` table and optionally POST to a Slack webhook URL in `TenantConfig`.

**Admin console.** Portal `/admin` page (gated to `org:admin` Clerk role): list all tenants, their run counts, costs, last active date. Read from `GET /api/usage?all_tenants=true` (add CE-internal-only auth check via `org_slug == "cardinal-element"`).

**Clerk Billing surface.** Portal `/billing` page: embed Clerk Billing portal component (Stripe-backed). No backend changes needed — Clerk handles subscription state.

**CI eval gate.** In `.github/workflows/` (or Railway deploy hook): after `pytest -m "not integration"` passes, run a small eval suite (`scripts/evaluate.py --protocol p03 --question Q1.1 --agents ceo cfo --dry-run`) with a judge threshold. Fail the deploy if overall score < 6.0. Store baseline scores in `smoke-tests/eval-baseline.json`.

**First-customer onboarding doc.** `docs/onboarding/CUSTOMER-ONBOARDING.md` — step-by-step: Clerk org creation → connector setup → first run → standing question setup → billing. (Create this only when Enhancement 8 is live.)

### Files to modify

| File | Change |
|------|--------|
| `CE - Multi-Agent Orchestration/api/models.py` | `error_code` on `Run`; new `TenantConfig` and `Notification` tables |
| `CE - Multi-Agent Orchestration/api/runner.py` | Map exceptions to `RunErrorCode` enum; emit `error` SSE event with code |
| `CE - Multi-Agent Orchestration/api/routers/usage.py` | Budget tracking: `GET /api/usage` with budget fields; `POST /api/usage/budget` |
| `cardinal-portal/` | `/admin` page; `/billing` Clerk embed; error card in RunDetail |
| `.github/workflows/` or Railway config | CI eval gate step |

### Effort: L

### Dependencies

Error codes can land independently. Budget alerts need APScheduler (Enhancement 8) for periodic checks, or can poll on run completion. CI eval gate should be the first item in this tier.

### Acceptance criteria

1. A timed-out run has `error_code="TIMEOUT"` in the DB and the portal RunDetail page shows "Request timed out — retry or reduce agent count."
2. When a tenant crosses 80% of their monthly budget, a `budget_alert` record is written to `notifications`.
3. `GET /api/usage` returns `monthly_budget_usd` and `budget_pct_used` for the calling tenant.
4. CI eval gate blocks a deploy when P03 overall score drops below 6.0.

---

## Sequenced Roadmap

```
Tier 1 — IN PROGRESS
  [1] Caching & resilience (S)
      Prompt caching in llm.py + server_agent.py
      Router memoization in router.py
      Agent-resolution lru_cache in agent_provider.py
      Per-tool timeout + circuit breaker in tool_executor.py

Tier 2 — Next sprint (order within tier is flexible)
  [2] Tool-call optimization (M)         — depends on [1] circuit breaker
  [3] Blackboard generalization (M)      — independent; Alembic migration needed
  [4] Router enhancements (M)            — independent
  [5] Conditional orchestration (M)      — depends on [4] router

Tier 3 — After Tier 2 stabilizes
  [7] Knowledge optimization (M)         — dedup + decay standalone; expiry needs [8]
  [8] Recurring research (L)             — depends on [5] pipeline resume + [7] graph score

Tier 4 — Productization
  [9] Usability & market utility (L)     — CI eval gate first; admin/billing last
  [6] Automated agent creation (L)       — depends on [9] eval gate

Dependency notes:
  - [8] Recurring Research depends on [5] (pipeline resume) and [7] (scored Decision nodes).
  - [6] Automated Agent Creation depends on [9] (eval gate + EvalRunner smoke-test infrastructure).
  - [3] Blackboard Generalization is partially unblocked now but durable persistence
    requires a ce-db migration pass coordinated with Tier 2.
  - All Tier 2+ changes that touch api/models.py must coordinate on a single Alembic
    migration to avoid conflicts on the Railway deploy.
```
