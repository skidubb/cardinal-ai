# Cardinal Element Multi-Agent Platform — Systems Engineering Assessment

**Date:** 2026-06-11  
**Scope:** Full monorepo snapshot, branch `claude/add-rc-config-support-W9iw7`  
**Assessor:** Claude Code (claude-sonnet-4-6), evidence drawn from direct file inspection

---

## 1. Executive Summary

The Cardinal Element platform is a production-grade, multi-tenant AI decision engine in late beta. It comprises:

- **57 coordination protocols** (P0a–P57) spanning liberating structures, intelligence analysis, game theory, systems thinking, and decentralized coordination
- **62-agent registry** backed by 80 hand-authored role prompts and 27 tool schemas
- **FastAPI backend** deployed on Railway with SSE streaming, PDF export (WeasyPrint), and Langfuse/Postgres observability
- **Next.js 16 portal** (`cardinal-portal/`) on Vercel, authenticated via Clerk Organizations (= tenants), with Stripe billing scaffolded
- **ce-graph** (Graphiti + FalkorDB) providing multi-tenant knowledge graph with 12+ entity types
- **Pinecone** semantic memory (index `ce-c-suite-learning`) per agent role
- **CE-Evals** library: multi-model blind judge with Borda ranking

**Status:** End-to-end core is working. Smart Route (portal → adaptive router → protocol run → PDF) shipped in commit `03177c3`. Pre-first-paying-customer. Gaps are concentrated in four areas: caching (none at any layer), resilience (silent failures, no circuit breaker), knowledge freshness (no recurring ingestion), and eval integration (manual-only, disconnected from routing).

---

## 2. Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│  cardinal-portal (Vercel — Next.js 16 + Clerk)                         │
│  Auth / Orgs / Billing / Dashboard / Smart Route UI / Discover         │
│  21 routes — prod: dashboard, run, history, agents, graph, discover    │
│  Stubs: /admin, /billing                                                │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  Clerk JWT (org_slug claim)
                             │  POST /api/router/decide
                             │  POST /api/router/run/with-context (multipart)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FastAPI backend (Railway)                                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  P0a ReasoningRouter                                             │  │
│  │  4 Haiku phases: features → problem type/confidence →            │  │
│  │  protocol selection (registry.build_routing_prompt_section())    │  │
│  │                                                                  │  │
│  │  AdaptiveRouterOrchestrator (adaptive_router/orchestrator.py)    │  │
│  │  confidence tiers: high ≥ 80 / mid ≥ 50                         │  │
│  │  cost-tier ceiling; 12-protocol static allowlist                 │  │
│  └───────────────────────┬──────────────────────────────────────────┘  │
│                          │ resolves to protocol key                     │
│                          ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  api/runner.py — protocol executor                               │  │
│  │  dynamic import → orchestrator.run(question, agents, **kwargs)   │  │
│  │  SSE streaming per stage → client                                │  │
│  │  dual-write: SQLModel Run + ce-db runs table                     │  │
│  └───┬─────────────────┬────────────────┬───────────────────────────┘  │
│      │                 │                │                               │
│      ▼                 ▼                ▼                               │
│  ServerAgent       graph_writer    cost_tracker                        │
│  (direct API,      (FalkorDB       (Postgres)                          │
│   tool loop        Decision node,                                       │
│   max 15 iter)     best-effort)                                        │
└──┬────────────┬────────────────────────────────────────────────────────┘
   │            │
   ▼            ▼
Anthropic    External tools (SEC EDGAR, GitHub, Census, BLS,
API          Brave Search, Notion, Pinecone, image gen, pricing)
             via api/tool_executor.py → CE Agent Builder tool registry

┌─────────────────────┐   ┌────────────────────────┐   ┌──────────────┐
│  ce-graph           │   │  Pinecone               │   │  Postgres    │
│  (FalkorDB)         │   │  ce-c-suite-learning    │   │  (Railway)   │
│  per-tenant graph   │   │  per-role namespaces    │   │  Run/runs    │
│  Decision/Lesson    │   │  no dedup/decay/expiry  │   │  dual-write  │
│  12+ entity types   │   │  manual backfill only   │   │  AgentOutput │
└─────────────────────┘   └────────────────────────┘   └──────────────┘

CE-Evals (standalone library — manual only, not wired into router or CI)
```

---

## 3. Per-Area Findings

### 3.1 Router

**Current state:** Two-tier routing. P0a (`protocols/p0a_reasoning_router/orchestrator.py`) runs four sequential Haiku phases to classify the question by problem type and confidence, then builds a routing prompt from `registry.build_routing_prompt_section()`. The AdaptiveRouterOrchestrator (`protocols/adaptive_router/orchestrator.py:91–153`) applies confidence thresholds (high ≥ 80, mid ≥ 50) and a cost-tier ceiling to select a final protocol. Smart Route is live in the portal (`commit 03177c3`), exposing `/api/router/decide` and `/api/router/run/with-context`.

**Strengths:** Clean separation of classification (P0a) from dispatch (adaptive). Confidence tiers prevent low-confidence routing from reaching expensive protocols. Cost-tier enforcement prevents runaway spend.

**Gaps:**
1. **Static 12-protocol allowlist.** `protocols/adaptive_router/resolver.py:26–41` hard-codes `DEFAULT_ALLOWLIST` to 12 of 57 protocols. The other 45 protocols — including all Wave 2 and Decentralized Coordination protocols — are unreachable via the router. Expansion requires a code change, not config or eval data.
2. **No learning feedback.** Eval scores from CE-Evals are never fed back to adjust protocol rankings or confidence thresholds. Router confidence is frozen at authoring time.
3. **No agent-roster awareness.** The router selects protocols without checking whether the requested agents have the capability to run them (e.g., agent-count constraints from `capability.yaml` are only enforced in the resolver after selection).
4. **No memoization.** Identical questions route through all four Haiku phases on every call. No caching of routing decisions.

**Evidence:**
- `protocols/adaptive_router/resolver.py:26–41` — `DEFAULT_ALLOWLIST` frozenset
- `protocols/adaptive_router/orchestrator.py:91–153` — confidence tier dispatch
- `protocols/p0a_reasoning_router/orchestrator.py` — 4-phase classification

---

### 3.2 Blackboard / Shared State

**Current state:** P54 Blackboard (`protocols/p54_blackboard/orchestrator.py:65–312`) is the only protocol using a shared state pattern. Implementation is in-memory: a `BlackboardEntry` list, a tick scheduler, and full-snapshot re-render on every tick. After any protocol run, `graph_writer.py:52–119` writes a `Decision` node to the tenant's FalkorDB graph (called from `runner.py:540–545`, best-effort with silent failure). Institutional memory is injected pre-run only, via `context_assembler` (`runner.py:264–275` → `server_agent.py:222–268` system prompt injection).

**Strengths:** Graphiti FalkorDB per-tenant graph is architecturally correct for durable shared state. Decision node writes provide audit trail across runs. Pre-run context injection works end-to-end.

**Gaps:**
1. P54's in-memory blackboard has no persistence — a crash or disconnect during a run loses all intermediate contributions.
2. JSON contribution parsing in P54 is fragile (string matching on free-form LLM output).
3. Blackboard is append-only with no conflict resolution or merge logic.
4. Post-run graph writes are fire-and-forget: errors are logged (`runner.py:546–549`) but not surfaced to the user or retry queue.
5. Mid-run agents cannot read from the graph — shared state is only available at run boundaries.

**Evidence:**
- `protocols/p54_blackboard/orchestrator.py:65–312`
- `CE - Multi-Agent Orchestration/protocols/graph_writer.py:52–119`
- `api/runner.py:540–549`

---

### 3.3 Caching

**Current state:** No prompt caching at any layer. `protocols/llm.py:157` reads `cache_read_input_tokens` from usage (for cost accounting) but never sends `cache_control` blocks. System prompts (80 role prompts averaging several hundred tokens each) are reconstructed and re-sent on every API call. Three narrow LRU caches exist for registry/manifest discovery: `registry._discover_protocols_cached`, `resolver._load_manifest`, `api/manifest._STAGES_CACHE`.

**Strengths:** Cost-accounting already tracks cache reads, so the plumbing for measuring cache benefit exists. LRU caches on manifest discovery avoid repeated YAML disk reads.

**Gaps:**
1. **No Anthropic prompt caching.** System prompts and tool schemas — the highest-volume repeated content — are never marked with `cache_control`. Estimated savings on a typical multi-agent run: 60–80% of input token cost for the system prompt portion.
2. `build_production_agents()` (`protocols/agent_provider.py:72`) re-resolves `_ROLE_PROMPTS` and `ROLE_TOOL_MAP` on every run. These are module-level constants; a singleton agent pool per tenant per session would eliminate this.
3. Tool schemas (`ALL_TOOL_SCHEMAS`, 27 definitions) are re-attached to every API call regardless of which tools the agent will use in that specific protocol context.
4. No router memoization: repeated identical questions trigger all four Haiku classification phases.

**Evidence:**
- `protocols/llm.py:156–157` — cache_read_input_tokens read but no cache_control sent
- `protocols/adaptive_router/resolver.py:14` — functools import (used only for `@functools.lru_cache`)
- `protocols/agent_provider.py:72` — `build_production_agents()` called per-run

---

### 3.4 Tool Use

**Current state:** `ServerAgent` (`protocols/server_agent.py:166–406`) implements a native tool-use loop with a maximum of 15 iterations. Tool calls within a single iteration are executed sequentially, one at a time. All tools mapped to a role are sent in every API call (no per-call pruning). Tool errors are returned as `{"error": ...}` data with no retry at the tool level. Tool results are capped at 50,000 characters (`api/tool_executor.py:24`). 27 tool schemas defined in `CE - Agent Builder/src/csuite/tools/schemas.py`; 66 role-to-tool mappings in `tools/registry.py:45–327`.

**Strengths:** 15-iteration ceiling prevents infinite tool loops. 50KB result cap prevents context overflow from large external API responses. Per-role tool mapping correctly scopes tool access.

**Gaps:**
1. **Sequential tool execution.** Multiple tool calls in a single LLM response are dispatched one by one. Parallel independent tool calls (e.g., SEC EDGAR + BLS API) could be batched with `asyncio.gather`.
2. **No per-tool timeout.** A stalled external API call blocks the entire agent turn indefinitely. There is no `asyncio.wait_for` wrapper in `api/tool_executor.py`.
3. **No tool-level retry.** Tool errors are returned as data to the LLM for it to handle; there is no exponential backoff at the tool execution layer (only at the LLM API call layer in `llm.py:50–81`).
4. **Full tool schema sent every call.** A CEO agent on a simple synthesis protocol still receives all its mapped tool schemas. Token overhead grows with role scope.

**Evidence:**
- `api/tool_executor.py:24` — `MAX_RESULT_LENGTH = 50_000`
- `protocols/server_agent.py:166–406` — tool loop, sequential dispatch
- `CE - Agent Builder/src/csuite/tools/schemas.py` — 27 tool definitions
- `CE - Agent Builder/src/csuite/tools/registry.py:45–327` — `ROLE_TOOL_MAP`

---

### 3.5 Protocol Architecture

**Current state:** 57 protocols, each in `protocols/p{NN}_{name}/` with `orchestrator.py`, `prompts.py`, `run.py`. `capability.yaml` per protocol declares `protocol_id`, `category`, `problem_types`, `cost_tier`, `min/max_agents`, `supports_rounds`, `stages`, and `recommended_agents`. Dynamic discovery at `api/runner.py:47–95` with selective `**kwargs` forwarding. `api/manifest.py:41–135` infers orchestration pattern from `stages`. Two-tier model strategy: Opus for reasoning, Haiku for mechanical steps.

**Strengths:** Protocol taxonomy is comprehensive and well-structured. The `capability.yaml` schema provides machine-readable metadata that the router and manifest can query. Async throughout; `asyncio.gather` for parallel agent queries. The two-tier model strategy is well-calibrated for cost/quality tradeoffs.

**Gaps:**
1. **No protocol versioning.** A breaking change to an orchestrator's output schema affects all in-flight and historical runs without migration. No semver or `schema_version` field in `capability.yaml`.
2. **No per-tenant protocol overrides.** Every tenant sees the same protocol implementation; there is no mechanism to parameterize a protocol differently for a customer (e.g., custom stage prompts, agent subsets).
3. **`asyncio.gather(return_exceptions=True)` silently drops failed agents.** Across `protocols/stages.py:51`, `270`, `327` and multiple individual protocol orchestrators, exceptions are filtered out of results without notifying the user that their roster was reduced. A 3-agent run that loses one agent silently becomes a 2-agent run.
4. **Silent partial results.** The only downstream signal of a dropped agent is `protocols/llm.py:572–577` (`gather_exceptions_ok()`), which returns exceptions as values — there is no top-level aggregation that counts drops and warns the user.

**Evidence:**
- `protocols/stages.py:51`, `270`, `327` — `return_exceptions=True` without warning emission
- `protocols/llm.py:572–577` — `gather_exceptions_ok()`
- Selected `capability.yaml` files (e.g., `protocols/p06_triz/capability.yaml`) — no `schema_version` field

---

### 3.6 Agent Creation and Registry

**Current state:** All agents are hand-authored. `CE - Agent Builder/src/csuite/agents/sdk_agent.py` contains `_ROLE_PROMPTS` (80 role-specific system prompts). `tools/registry.py:45–327` contains `ROLE_TOOL_MAP` (66 roles). `protocols/agents.py` defines 62 `BUILTIN_AGENTS`. `agent_provider.build_production_agents()` applies DB overrides for `model` and `temperature` at runtime. Portal has custom-agent CRUD but no generation, no A/B prompt testing, and no eval gate before a custom agent is promoted to production use.

**Strengths:** Role prompts are high-quality and differentiated. Per-role tool scoping is fine-grained. DB override mechanism allows per-customer model/temperature tuning without code deploys.

**Gaps:**
1. **100% manual authoring.** Adding a new agent role requires editing `_ROLE_PROMPTS` (80-entry dict), `ROLE_TOOL_MAP`, and `BUILTIN_AGENTS` across three files in two packages. No generation assist, no template.
2. **No eval gate for custom agents.** A portal user can create a custom agent and deploy it to live runs with no quality assessment. CE-Evals is not wired into the agent creation workflow.
3. **No A/B testing.** There is no mechanism to run two versions of a prompt against the same question and compare outputs via the eval framework.
4. **No agent-level capability declarations.** Unlike protocols (which have `capability.yaml`), agents have no machine-readable metadata about their strengths, cost tier, or recommended protocol pairings.

**Evidence:**
- `CE - Agent Builder/src/csuite/agents/sdk_agent.py` — `_ROLE_PROMPTS` dict
- `CE - Agent Builder/src/csuite/tools/registry.py:45–327` — `ROLE_TOOL_MAP`
- `protocols/agents.py` — `BUILTIN_AGENTS` (62 entries)

---

### 3.7 Knowledge Layer

**Current state:** `ce-graph` (Graphiti + FalkorDB) provides per-tenant knowledge graphs with 12+ entity types: `Client`, `Engagement`, `Protocol`, `Decision`, `Correction`, `Lesson`, and others (`ce-graph/src/ce_graph/entities.py`). Tenant isolation via `tenancy.py`; deterministic Cypher helpers in `queries.py`; semantic search via `GraphClient.search()`. Six canonical tenants are provisioned; additional tenants auto-provisioned from Clerk org slugs.

Pinecone index `ce-c-suite-learning` provides semantic memory with per-role namespaces (`CE - Agent Builder/src/csuite/memory/store.py:1–84`). Records are stored with `record_id = f"{role}-{int(time.time() * 1000)}"` (line 45) — no semantic deduplication, no decay, no expiry TTL.

**Strengths:** Multi-tenant FalkorDB isolation is architecturally sound. `Correction` and `Lesson` entity types provide the scaffolding for a learning loop. Graphiti's temporal fact model supports versioned institutional memory. Pinecone integrated inference eliminates local embedding model dependency.

**Gaps:**
1. **No deduplication in Pinecone.** Every `store()` call generates a new record with a timestamp-based ID (line 45). Repeated analysis of the same topic accumulates unbounded duplicate embeddings. There is no similarity check before upsert.
2. **No memory decay or expiry.** Old records from months-ago sessions persist at equal weight with recent ones. Retrieval quality degrades as the index grows.
3. **Connectors are manual-trigger only.** Notion, HubSpot, and Granola integrations are backfill scripts; there is no scheduled ingestion. Knowledge graphs stagnate between manual runs (see §3.8).
4. **Graph write failures are invisible to users.** Post-run `write_decision()` errors are logged at WARNING level (`runner.py:547–549`) but not surfaced in the UI or persisted as a warning on the run record.
5. **Pre-run context injection only.** Agents can read the knowledge graph before a run starts, but cannot query it mid-run as new information surfaces during the protocol. The graph is a read-only input, not a live shared resource.

**Evidence:**
- `CE - Agent Builder/src/csuite/memory/store.py:45` — timestamp-ID record with no dedup
- `api/runner.py:540–549` — best-effort `write_decision()` with silent failure
- `runner.py:264–275` — pre-run context injection (only occurrence)

---

### 3.8 Recurring Research / Knowledge Freshness

**Current state:** No scheduled research or ingestion pipeline exists anywhere in the codebase. Two exploratory n8n workflow JSON exports are present in `n8n Workflows/` but neither implements recurring protocol runs or connector sync. There is no cron scheduler, no `CronCreate` invocation, and no worker process for background ingestion.

**Strengths:** Protocol architecture (async, deterministic) is well-suited for scheduled headless runs. The `runs` table and Langfuse tracing would capture scheduled run output without code changes.

**Gaps:**
1. The platform is entirely reactive: it responds to user-initiated runs. No proactive knowledge refresh.
2. Market intelligence, competitor data, and connector-sourced facts (Notion, HubSpot, Granola) go stale without manual re-runs.
3. There is no mechanism to schedule a protocol (e.g., P32 Tetlock Forecast) to run weekly and store results in ce-graph as `Lesson` nodes.
4. No staleness indicator in the portal's knowledge graph view to alert users that graph data is N days old.

---

### 3.9 Evals

**Current state:** `CE - Evals` library implements `BlindJudge` (anonymized candidates, multi-model judging, Borda ranking) with three LLM backends (Anthropic/OpenAI/Gemini). `EvalRunner` persists results to Postgres best-effort. `scripts/evaluate.py` runs the harness against 34 benchmark questions across 8 problem types. The API exposes a `judge_verdict` field on the `Run` model for per-run quality assessment.

**Strengths:** Borda ranking with multi-model judging reduces single-model bias. Blind evaluation (anonymized candidates) reduces position bias. Three-backend design hedges against any one provider's idiosyncrasies.

**Gaps:**
1. **Manual-only.** No CI integration, no automated regression detection. There is no job that runs on merge to detect protocol quality regressions.
2. **Disconnected from router.** Eval scores are never fed back to `DEFAULT_ALLOWLIST`, confidence thresholds, or protocol rankings in the adaptive router. The router cannot learn which protocols perform better on which problem types.
3. **No regression baseline.** No stored "golden" eval results to diff against. Each eval run is a one-shot assessment with no historical comparison.
4. **Research-mode contamination risk.** Per MEMORY.md, eval scores from research-mode runs (agents as dicts, no tools) are invalid for production quality assessment. There is no mode flag on stored eval results to identify this.

**Evidence:**
- `CE - Evals/src/ce_evals/core/judge.py` — BlindJudge implementation
- `scripts/evaluate.py` — manual harness runner
- `protocols/adaptive_router/resolver.py:26–41` — no eval feedback in allowlist

---

### 3.10 Resilience

**Current state:** `protocols/llm.py:32–81` implements 3-retry exponential backoff (delays: 1s, 2s, 4s + ≤0.5s jitter) for `RateLimitError`, `APIConnectionError`, and 5xx status codes. `asyncio.gather(return_exceptions=True)` is used at `protocols/stages.py:51`, `270`, `327` and in individual protocol orchestrators. Post-run persistence uses a 2-layer write: SQLModel `Run` table (UI-facing) and the Alembic-managed `runs` table (audit sink). Graph writes are best-effort. SSE heartbeat runs at 5-second intervals with client-disconnect cancellation handling.

**Strengths:** Retry logic is well-implemented with jitter to prevent thundering herds. SSE heartbeat + disconnect handling prevents zombie runs from consuming compute. Two-layer persistence provides redundancy for run records.

**Gaps:**
1. **No circuit breaker.** If the Anthropic API degrades (sustained 529s), the retry loop will exhaust all attempts on every call in the run, compounding latency with no fast-fail path. `CE - Agent Builder/src/csuite/tools/resilience.py` has a circuit breaker implementation but it is not wired into the production API path.
2. **Silent agent drops.** `asyncio.gather(return_exceptions=True)` silently reduces agent rosters when agents fail. The SSE stream and final output do not indicate which agents succeeded vs. failed.
3. **No tool-level timeout.** Tool execution in `api/tool_executor.py` has no `asyncio.wait_for` wrapper. A stalled Brave Search or SEC EDGAR call can block an agent turn for the full TCP timeout (minutes).
4. **No fallback model.** If Opus is unavailable, there is no automatic downgrade to Sonnet. The `fallback_model` parameter in `protocols/llm.py:260` is a caller-supplied default, not an automatic degradation path.
5. **Dual-write debt.** Two run-tracking schemas (`run` SQLModel table and `runs` Alembic table) are both load-bearing. A write failure to either is logged but not retried, creating the possibility of UI-visible runs with no audit record (or vice versa). Schema divergence risk increases as the two schemas evolve independently.

**Evidence:**
- `protocols/llm.py:32–81` — `_retry_api_call()` implementation
- `protocols/stages.py:51`, `270`, `327` — silent exception filtering
- `api/tool_executor.py:24` — no timeout in tool dispatch
- `CE - Agent Builder/src/csuite/tools/resilience.py` — circuit breaker exists but not wired to production path
- `CE - Multi-Agent Orchestration/docs/schema.md` — dual-write schema documentation

---

### 3.11 Product / Usability / Market Readiness

**Current state:** `cardinal-portal/` is a Next.js 16 application with Clerk auth, 21 routes, and Stripe billing scaffolding. Production-ready features include: smart-route run form with file context upload, run history with PDF export, agents/teams/pipelines CRUD, knowledge graph view, discover (document → questions → protocol mapping), and corrections. Stubs exist for `/admin` and `/billing`. Tenant scoping is enforced end-to-end via Clerk JWT `org_slug` → every API query filtered in `api/middleware/clerk_auth.py`.

The research-era Vite app (`ui/`) remains in the repo as an unauthenticated internal harness, creating feature-parity confusion.

**Strengths:** Clerk handles auth, Organizations, and billing UI, eliminating significant surface area. Tenant scoping is architecturally enforced at middleware, not sprinkled per-endpoint. Smart Route and PDF export provide a complete user-facing workflow. Discover flow (doc → questions → protocol) is a differentiating UX.

**Gaps:**
1. **No cost estimates or budget alerts.** Users cannot see projected cost before starting a run, and there are no per-tenant budget caps or overage alerts.
2. **Raw error strings.** API errors propagate as unstructured strings to the portal. There is no error taxonomy or user-friendly messaging layer.
3. **No run scheduling.** Users cannot schedule a protocol to run at a future time or on a recurring basis from the portal.
4. **No per-user cost split.** Cost tracking is per-tenant (org slug); within a multi-member organization there is no per-user attribution.
5. **Pipeline resume is incomplete.** `api/routers/pipelines.py` has a `resume/{run_id}` endpoint stub but the checkpoint/resume logic is not fully implemented.
6. **Dual UI surface confusion.** The old `ui/` Vite app and `cardinal-portal/` coexist. The Vite app is unauthenticated and lacks tenant scoping; a developer testing via the Vite app sees different behavior than a portal user.

**Evidence:**
- `cardinal-portal/` — 21 routes, Clerk-gated
- `api/middleware/clerk_auth.py` — JWT validation and `org_slug` extraction
- `api/routers/pipelines.py` — stub resume endpoint
- `CE - Multi-Agent Orchestration/ui/` — legacy Vite app

---

## 4. Risk Register

| # | Risk | Severity | Likelihood | Notes |
|---|------|----------|------------|-------|
| R1 | **Dual-write run/runs table debt** | High | High | Both tables are load-bearing (UI vs. audit). A write failure to either is silent. Schema divergence will widen as the system evolves. Mitigation: designate one table as source of truth; derive the other via a view or event. Reference: `docs/schema.md`. |
| R2 | **Silent persistence/graph-write failures** | High | High | `graph_writer` failures are logged at WARNING level and not surfaced to users or retried. A run can complete successfully in the UI while having no Decision node in the knowledge graph. Long-term: the knowledge graph becomes an unreliable, incomplete record of decisions. |
| R3 | **No circuit breaker on Anthropic API** | High | Medium | Sustained API degradation triggers full retry exhaustion on every agent call in a run. A 6-agent protocol run could accumulate 6 × 4 retry sequences before failing. The circuit breaker in `CE - Agent Builder/src/csuite/tools/resilience.py` is not wired into the production `llm.py` path. |
| R4 | **No per-tool timeout** | Medium | High | External tool calls (SEC EDGAR, Brave Search, BLS API) have no `asyncio.wait_for` wrapper. A stalled tool call blocks the agent turn for the TCP connection timeout. In production, this manifests as phantom-hung runs with no SSE output. |
| R5 | **Static 12-protocol router allowlist** | Medium | High | 45 of 57 protocols are unreachable via Smart Route. The allowlist is a code constant (`resolver.py:26–41`). As new protocols are validated, expanding the allowlist requires a code deploy. Evals should gate promotion automatically. |
| R6 | **Knowledge graph staleness** | Medium | High | No recurring ingestion pipeline. Connector backfills (Notion, HubSpot, Granola) are manual scripts. The knowledge graph stagnates between manual runs. Users have no staleness signal in the portal. |
| R7 | **Pinecone memory unbounded growth** | Medium | Medium | No deduplication, decay, or expiry on Pinecone records. `store()` generates a new record on every call (`store.py:45`). Retrieval quality will degrade as duplicate vectors accumulate. |
| R8 | **iCloud Documents venv eviction (local ops)** | Medium | High | Repo lives in `~/Documents` (iCloud-synced). iCloud marks venv files as "dataless" and evicts them, causing import failures that look like hangs at 0% CPU. Documented in MEMORY.md. Affects local dev reliability and CI-if-run-on-Mac. |
| R9 | **Silent agent roster reduction** | Medium | High | `asyncio.gather(return_exceptions=True)` drops failed agents silently across `stages.py:51`, `270`, `327` and multiple protocol orchestrators. A 4-agent run that fails 2 agents returns a 2-agent result with no user notification. |
| R10 | **No prompt caching** | Medium | High | System prompts and tool schemas are re-sent on every API call. On a 6-agent parallel synthesis run, each agent sends ~1,000+ tokens of repeated system prompt. Estimated 60–80% cache-able input token reduction is not captured. |
| R11 | **Research-mode eval contamination** | Low | Medium | CE-Evals does not tag whether a run was in research vs. production mode. Research-mode scores (no tools, dict agents) are structurally different from production-mode runs and should not be compared. No mode flag on stored eval records. |

---

## 5. Summary Maturity Table

| Area | Maturity | Key Gaps |
|------|----------|----------|
| **Protocol Architecture** | High | No versioning; silent agent drops; no per-tenant overrides |
| **Router** | Medium-High | Static allowlist (12/57); no eval feedback; no memoization |
| **Agent Registry** | Medium | 100% hand-authored; no eval gate; no capability declarations |
| **Tool Use** | Medium | Sequential dispatch; no per-tool timeout; no tool-level retry |
| **Knowledge Layer (ce-graph)** | Medium | Write failures invisible; mid-run read not possible |
| **Knowledge Layer (Pinecone)** | Low-Medium | No dedup, no decay, unbounded growth |
| **Caching** | Low | No prompt caching anywhere; re-sends full system prompts every call |
| **Recurring Research** | Low | Not implemented; no scheduler; connectors are manual-only |
| **Evals** | Low-Medium | Manual-only; disconnected from router; no regression baseline |
| **Resilience** | Medium | Retry ✓; circuit breaker missing; tool timeouts missing; silent drops |
| **Portal / Product** | Medium-High | Core flow working; no cost estimates; no scheduling; raw errors |
| **Multi-tenancy** | High | Clerk JWT scoping enforced at middleware across all paths |

**Overall platform maturity: late beta.** The core request-to-response loop (portal → router → protocol → agents → PDF) is working end-to-end and multi-tenant. The primary pre-GA gaps are operational reliability (circuit breaker, tool timeouts, surface silent failures) and unit economics (prompt caching, which directly affects margin at scale). The knowledge layer and evals are the longest-lead investments for sustained product differentiation.
