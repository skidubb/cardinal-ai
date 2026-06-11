# Cardinal Element Multi-Agent Platform — Quarterly Maturity Rubric

**Version:** 1.0  
**Created:** 2026-06-11  
**Branch scope:** `claude/add-rc-config-support-W9iw7`  
**Companion docs:** [SYSTEMS-ASSESSMENT.md](SYSTEMS-ASSESSMENT.md) · [ENHANCEMENT-PREP.md](ENHANCEMENT-PREP.md)

---

## How to Use This Document

**Purpose.** Score the platform once per quarter to track engineering maturity across eight categories. Scores inform sprint prioritization and serve as evidence in investor or customer conversations about platform reliability.

**Scale.** Each criterion is scored 1–5:

| Score | Meaning |
|-------|---------|
| 1 | Not implemented or fundamentally broken |
| 2 | Partial / manual / happy-path only |
| 3 | Working and measurable; gaps in edge cases or automation |
| 4 | Production-hardened; automated; observable |
| 5 | Best-in-class; self-improving or fully automated |

**Category score** is the unweighted average of its criteria, rounded to one decimal. Do not round to the nearest integer — fractional scores carry signal.

**How to measure.** Each criterion names a concrete measurement method — a file path, a Langfuse query, a Postgres table, or a portal behavior. The scorer should verify evidence directly, not from memory.

**Who scores.** Ideally one engineer and one non-technical stakeholder independently; reconcile on disagreements > 1 point. Document the scorer name(s) and any disputed criteria in the log at the end of this file.

**Cadence.** Score at the end of each calendar quarter (Q1 = March 31, Q2 = June 30, Q3 = September 30, Q4 = December 31). Mid-quarter re-scores are allowed after a major release but must be labeled "interim."

**Targets.** Two-quarter targets align with the ENHANCEMENT-PREP.md tier roadmap: Tier 1 and Tier 2 enhancements complete by Q3 2026, Tier 3 in progress by Q4.

---

## Category Anchors

Before scoring individual criteria, calibrate your interpretation using these category-level 1/3/5 anchors. Individual criteria may vary ±1 from the category average where specific evidence supports it.

| Category | Score 1 (floor) | Score 3 (working) | Score 5 (best-in-class) |
|----------|----------------|-------------------|------------------------|
| **Output Quality & Resilience** | No eval; silent failures; no error taxonomy | Per-run judge wired; partial failures surfaced; basic error codes | Regression CI gate; automatic rollback on score drop; zero silent failures |
| **Cost Efficiency** | No caching; full token resend every call; no cost visibility | Prompt caching active; router memoized; cost displayed pre-run | Adaptive tool pruning; batch API for overnight jobs; per-run margin tracked in Langfuse |
| **Routing Intelligence** | Hard-coded single protocol; no confidence scoring | Two-tier router with confidence thresholds; 25+ protocols routable | All protocols routable via config; eval-fed ranking; agent-roster awareness |
| **Orchestration Automation** | Manual single-step runs only | Conditional pipelines; resume works; auto-compose available | Self-healing pipelines; LLM-driven step selection; proactive re-runs on context change |
| **Knowledge Freshness** | Static knowledge; no graph writes; no Pinecone memory | Decision nodes written post-run; scheduled connector sync; dedup active | Mid-run graph reads; decay-weighted retrieval; standing questions with Lesson diffs |
| **Agent Factory Maturity** | All agents hand-authored; no portal creation; no eval gate | Opus-generated drafts with eval smoke gate; portal wizard live | Full A/B harness; auto-promote winners; capability declarations on all agents |
| **Usability** | Raw API errors; no cost visibility; no PDF; no run history | Cost estimate badge; human-readable errors; PDF export; run history | Scheduled runs; budget alerts; per-user cost split; real-time progress with stage ETA |
| **Market Readiness** | No tenant isolation; no billing; no admin console | Tenant isolation enforced; billing UI live; CI eval gate | Scheduler live; zero dual-write debt; onboarding doc; customer SLA monitoring |

---

## 1. Output Quality & Resilience

**Baseline category score: 2/5**

Evidence basis: per-run `judge_verdict` field exists on `Run` model but is not populated automatically; `asyncio.gather(return_exceptions=True)` silently drops agents at `protocols/stages.py:51,270,327`; no error taxonomy beyond raw exception strings; no CI regression gate. Retry logic in `protocols/llm.py:32–81` is well-implemented (scores this category above 1).

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Per-run eval coverage** | Fraction of completed production runs that have a `judge_verdict` score attached | `SELECT COUNT(*) FILTER (WHERE judge_verdict IS NOT NULL) / COUNT(*) FROM run WHERE status='completed'` in Railway Postgres | 2 — field exists but not auto-populated | 4 — all Smart Route runs auto-judged |
| **Silent failure rate** | Fraction of runs where at least one agent was silently dropped (exception swallowed by `return_exceptions=True`) with no SSE warning emitted | Langfuse: runs with `agent_drop_count > 0` that have no `tool_warning` or `agent_warning` event; or grep `stages.py` for `return_exceptions` without paired warning emission | 1 — no warning emitted; all drops are silent | 4 — every drop emits a `agent_warning` SSE event with agent key and reason |
| **Circuit breaker coverage** | Production API call path (`protocols/llm.py`) is guarded by a circuit breaker that opens after sustained failures | Check `api/tool_executor.py` and `protocols/llm.py` for `_ToolBreakerState` or equivalent; verify `CE - Agent Builder/src/csuite/tools/resilience.py` circuit breaker is wired in | 1 — circuit breaker exists in Agent Builder but not wired into `llm.py` (SYSTEMS-ASSESSMENT §3.10) | 4 — circuit breaker active; Langfuse shows `circuit_open` events |
| **Error taxonomy** | Structured `RunErrorCode` enum covers ≥ 5 error classes; portal renders human-readable card per code | Check `api/models.py` for `RunErrorCode`; portal RunDetail page for error card component | 1 — `error_message: Optional[str]` is raw exception text; no enum | 4 — 6+ error codes; portal renders suggested action per code |
| **Regression detection** | Automated baseline comparison: eval score drop of > 1.0 point vs. stored baseline triggers CI failure | `.github/workflows/` or Railway deploy hook runs `scripts/evaluate.py`; `smoke-tests/eval-baseline.json` exists | 1 — no CI eval gate; no baseline JSON | 3 — CI gate on P03 Q1.1 only; baseline JSON committed |

---

## 2. Cost Efficiency

**Baseline category score: 2/5**

Evidence basis: Tier 1 prompt caching and router memoization implemented in working tree (upgrades this from 1/5); no Anthropic Batch API usage; all 27 tool schemas sent on every API call regardless of protocol stage; `build_production_agents()` re-imports role prompts per run.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Prompt cache hit rate** | `cache_read_input_tokens / (cache_read_input_tokens + cache_creation_input_tokens)` across Opus protocol runs | Langfuse: custom metric from `usage_details`; or Railway log grep for `cache_read_input_tokens` | 2 — tracking implemented in `llm.py:157`; `cache_control` blocks added in working tree but not yet verified in production | 4 — ≥ 60% cache hit rate on Opus runs verifiable in Langfuse |
| **Router memoization coverage** | Fraction of `/api/router/decide` calls served from TTL cache (no Haiku phases executed) | Router TTL dict hit/miss log in `api/routers/router.py`; Langfuse span count for P0a on repeat questions | 2 — memoization implemented in working tree | 4 — hit rate ≥ 40% in production (repeat question traffic) |
| **Tool schema pruning** | Fraction of agent turns where only stage-relevant tool schemas are sent (not full role set) | Inspect `create_kwargs["tools"]` count in `protocols/server_agent.py`; compare to `ROLE_TOOL_MAP` cardinality for the same role | 1 — all mapped tools sent every call; no `allowed_tools` filtering | 3 — `tools_subset` in `capability.yaml` for P06, P16, P32; per-stage pruning active |
| **Batch API usage** | Long-running headless protocol runs (scheduled research, eval regression) use Anthropic Batch API when latency-insensitive | `api/runner.py` — `run_protocol_headless()` has a `use_batch=True` path; Anthropic Batch dashboard shows CE usage | 1 — no headless run path; no Batch API integration | 3 — headless path exists; standing question runs optionally use Batch |
| **Agent resolution caching** | `build_production_agents()` uses `lru_cache` or equivalent; no re-import of `_ROLE_PROMPTS` after first call per worker | Inspect `protocols/agent_provider.py` for `@lru_cache`; verify via process-level timing log or Langfuse `agent_build_ms` span | 2 — re-import per call currently; `lru_cache` targeted in Tier 1 | 4 — lru_cache active; agent build time < 5 ms on cache hit |

---

## 3. Routing Intelligence

**Baseline category score: 2/5**

Evidence basis: two-tier router (P0a + AdaptiveRouterOrchestrator) works end-to-end; only 12 of 57 protocols in `DEFAULT_ALLOWLIST` (`protocols/adaptive_router/resolver.py:26–41`); eval scores never fed back to routing prompt; no agent-roster capability check before selection.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Protocol coverage** | Fraction of 57 protocols reachable via Smart Route without a code change | Count `routable: true` entries in `capability.yaml` files; or count non-`DEFAULT_ALLOWLIST` protocols that can be selected | 2 — 12/57 (21%) routable; expansion requires code change to `resolver.py:26–41` | 4 — ≥ 45/57 (79%) routable via `routable: true` yaml field; static list is fallback only |
| **Eval-fed routing** | Protocol performance scores from CE-Evals appear in the P0a routing prompt and influence selection | `protocols/registry.py:build_routing_prompt_section()` accepts `db_session`; Langfuse P0a system prompt includes "Protocol performance" block | 1 — routing prompt has no historical data; `build_routing_prompt_section()` is static | 3 — tenant-level avg judge score appended to routing prompt when ≥ 5 runs exist per protocol |
| **Pre-run cost estimate** | `/api/router/estimate` endpoint returns cost range before run submission; portal RunForm displays badge | `api/routers/router.py` has `POST /estimate`; portal RunForm component calls it | 1 — no estimate endpoint; no portal badge | 4 — estimate badge shown on question change (debounced 800 ms) per ENHANCEMENT-PREP §4 |
| **Agent-roster awareness** | Router validates that requested agents satisfy `min_agents`/`max_agents` from `capability.yaml` before confirming protocol selection | `protocols/adaptive_router/resolver.py` — `_load_manifest()` checks roster against capability constraints; resolver rejects and re-routes when violated | 2 — `capability.yaml` constraints exist but are enforced only after selection, not during routing | 3 — pre-selection roster check; user gets informative rejection with suggested roster fix |
| **Learning loop** | Router decision quality improves measurably over a rolling 90-day window (lower re-run rate, higher avg judge score on first-run protocols) | Langfuse: compare `judge_verdict` avg for router-selected vs. manually-selected protocols over 30/60/90-day windows | 1 — no feedback loop; eval scores not stored with routing metadata | 3 — routing decision logs include selected protocol + judge score; trend dashboard in Langfuse |

---

## 4. Orchestration Automation

**Baseline category score: 2/5**

Evidence basis: manual linear pipelines with fixed step lists; `POST /api/pipelines/resume/{run_id}` endpoint exists but replays from step 0 (SYSTEMS-ASSESSMENT §3.11); no conditional branching on `PipelineStep`; no auto-composition.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Pipeline resume fidelity** | A pipeline restarted after interruption continues from the last completed `RunStep`, not from step 0 | `POST /api/pipelines/resume/{run_id}` test: interrupt at step 2 of 4; resume; verify via `RunStep` rows that steps 1–2 are not re-executed | 1 — resume exists as stub; replays from step 0 per ENHANCEMENT-PREP §5 | 4 — resume verified to skip completed steps; prior step output injected as context |
| **Conditional branching** | Pipeline steps support a `condition` expression that skips or escalates based on prior step output | `api/models.py:PipelineStep` has `condition: str | None`; test pipeline with `"confidence < 50"` skips heavy protocol when not needed | 1 — no `condition` field on `PipelineStep` | 3 — condition evaluator live; 3+ production pipelines use branching |
| **Auto-composition** | `POST /api/router/compose` returns a 1–3 step pipeline for a given question without user manually selecting protocols | `api/routers/router.py` has `/compose` endpoint; returns `{pipeline: [{protocol_key, rationale}], total_estimated_cost}` in < 5 s | 1 — endpoint does not exist | 3 — endpoint live; tested on 5+ question types; single-step and 2-step pipelines working |
| **Protocol output chaining** | Each pipeline step receives the structured output of the prior step as input, not the original raw question | `api/runner.py:run_pipeline_stream()` — verify `context_injection` for step N+1 contains step N `result_summary`; check Langfuse traces for context propagation | 2 — runner passes same question to each step independently | 4 — output chaining verified via Langfuse trace; per MEMORY.md protocol chaining rule |
| **Headless run path** | Protocols can be invoked without SSE (batch/scheduled mode) and return a `RunEnvelope` directly | `api/runner.py` has `run_protocol_headless()`; APScheduler can call it; verify via a manually triggered cron-style invocation | 1 — `run_protocol_stream()` is the only entrypoint; SSE required | 3 — headless path live; standing question scheduler uses it |

---

## 5. Knowledge Freshness

**Baseline category score: 2/5**

Evidence basis: multi-tenant FalkorDB + Pinecone infrastructure is rich; graph writes are post-run and best-effort (silent failure at `runner.py:540–549`); no scheduled connector sync; no Pinecone dedup; pre-run context injection only (`runner.py:264–275`); no staleness signal in portal.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Graph write reliability** | Fraction of completed runs where `Decision` node was successfully written to FalkorDB | Postgres: `SELECT COUNT(*) FILTER (WHERE graph_write_status='success') / COUNT(*) FROM run WHERE status='completed'`; or Langfuse `graph_write` span success rate | 2 — writes are best-effort; failures logged at WARNING only; no write status on `Run` model | 4 — `graph_write_status` column on `Run`; alert if success rate < 90% in 24 h |
| **Connector sync cadence** | At least one tenant has at least one connector (Notion/HubSpot/Granola) syncing on a scheduled cron | `api/models.py:Integration` has `sync_cadence_cron`; APScheduler job registered; last sync timestamp < 24 h ago | 1 — no scheduled sync; connectors are manual backfill scripts only | 3 — Notion connector syncing on schedule for ≥ 1 tenant; portal shows last-sync timestamp |
| **Pinecone dedup rate** | Fraction of `MemoryStore.store()` calls that are skipped due to semantic similarity > 0.95 with an existing record | Instrument `CE - Agent Builder/src/csuite/memory/store.py:store()` to log skip vs. upsert; check log ratio over 7 days | 1 — no dedup; every call upserts (`store.py:45` timestamp ID); duplicates accumulate | 3 — dedup query active; skip rate logged; < 20% of stores are duplicates |
| **Retrieval recency weighting** | `MemoryStore.retrieve()` applies decay scoring so a 2-year-old record ranks below a 30-day-old record at equal similarity | Unit test: insert two identical-content records with dates 2 years apart; verify newer record ranks higher in `retrieve()` result | 1 — retrieval is pure similarity ranking; no age weighting | 3 — exponential decay active (`exp(-age_days/90)`); unit test passes |
| **Mid-run graph access** | Agents can read from FalkorDB during a protocol run (not just at run start) | `api/runner.py` — `mid_run_graph_reads` flag; Langfuse traces show `context_assembler` calls between stages, not just at run start | 1 — context injected once pre-run at `runner.py:264–275`; no mid-run reads | 3 — mid-run reads enabled (gated flag); active on ≥ 1 protocol (P54 Blackboard) |
| **Knowledge staleness signal** | Portal knowledge graph view shows last-updated timestamp per tenant and warns when > N days stale | Portal `ce-graph` view component; `GET /api/graph/status` endpoint returns `last_write_at` per tenant | 1 — no staleness indicator; no API endpoint for graph recency | 3 — last-write timestamp shown in portal; yellow warning if > 7 days |

---

## 6. Agent Factory Maturity

**Baseline category score: 1/5**

Evidence basis: 100% hand-authored — 80 prompts in `_ROLE_PROMPTS`, 66 tool maps in `ROLE_TOOL_MAP`, 62 agents in `BUILTIN_AGENTS`; portal has CRUD for custom agents but no generation endpoint; CE-Evals not wired into agent activation; no A/B mechanism; no `capability.yaml` equivalent for agents.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Agent generation** | `POST /api/agents/generate` produces a system prompt + tool list from a role description via Opus meta-prompt | `api/routers/agents.py` has `/generate` endpoint; responds in < 30 s with `system_prompt` and `tools_json` | 1 — no generate endpoint; all agents hand-authored | 3 — endpoint live; tested on 5+ role descriptions; output quality reviewed by Scott |
| **Eval gate on activation** | Custom agents cannot be set to `status='active'` without passing CE-Evals smoke gate (3 questions, Borda comparison vs. 2 nearest builtins) | `CE - Evals/src/ce_evals/core/runner.py` has `run_smoke_test()`; `Agent.status` field with `pending_eval/active/archived`; verify via portal wizard flow | 1 — no eval gate; portal CRUD allows immediate activation | 3 — smoke gate runs on generation; sub-threshold agents stay `pending_eval`; human can override |
| **A/B harness** | Portal supports `ab_test=True` flag on custom agents; router 50/50 splits between builtin and custom variant; auto-promotes after 20 runs | `api/models.py:Agent.ab_test` field; `api/runner.py` split logic; Langfuse `ab_variant` tag on runs | 1 — no A/B mechanism anywhere | 2 — A/B flag exists on model; split logic not yet implemented |
| **Agent capability declarations** | Each agent has machine-readable metadata (cost tier, recommended protocol pairings, domain tags) analogous to protocol `capability.yaml` | `protocols/agents.py:BUILTIN_AGENTS` entries carry `cost_tier`, `domains`, `recommended_protocols` fields; or a per-agent `capability.yaml` | 1 — agents are key → name/description dicts only; no metadata beyond display name | 3 — cost tier and 3+ domain tags on all 62 builtin agents; router uses domain tags for selection |
| **Portal wizard completeness** | End-to-end flow: role description → generated prompt preview → eval results → activate/discard works without developer intervention | Portal `/agents/new` route exists; test via portal UI; no backend console commands needed | 1 — no `/agents/new` route; custom agents require direct API calls | 3 — wizard covers generation + eval gate; activate/discard works; no dev console needed |

---

## 7. Usability

**Baseline category score: 3/5**

Evidence basis: working end-to-end Smart Route flow (portal → router → protocol → PDF) shipped in commit `03177c3`; PDF export via WeasyPrint; run history; discover flow (doc → questions → protocol); raw error strings with no taxonomy; no cost estimates pre-run; first-run latency opaque during protocol execution.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Pre-run cost estimate** | Portal RunForm displays estimated cost range and protocol selection before submission | Portal RunForm calls `/api/router/estimate`; badge visible in browser; no submission required | 1 — no estimate shown; user submits blind | 4 — badge updates on question change (debounced); shows protocol name + cost range |
| **Human-readable errors** | Portal renders a structured error card (title, reason, suggested action) instead of raw exception text | Portal RunDetail page: check for error card component; simulate a `TIMEOUT` run; verify card vs. raw string | 2 — `error_message` shown as raw text in portal (SYSTEMS-ASSESSMENT §3.11) | 4 — error card per `RunErrorCode`; includes "Retry", "Reduce agents", or "Contact support" CTA |
| **Stage progress transparency** | SSE stream delivers per-stage progress events; portal shows stage name, elapsed time, and remaining stage count during a run | Portal RunDetail progress bar; Langfuse SSE event log; verify `{"event": "stage_start", "stage_name": ..., "stage_index": ..., "total_stages": ...}` events emitted | 3 — SSE streaming works; stage events emitted; portal shows spinner but not stage names | 4 — stage names + index/total visible in portal; ETA estimate shown for long protocols |
| **PDF export quality** | PDF reports are generated for ≥ 90% of completed runs; include all agent outputs, protocol metadata, and Borda scores when available | Test via portal "Export PDF" button on a completed run; WeasyPrint log for errors; check PDF content for protocol name, agents, outputs | 3 — PDF export works for most runs; WeasyPrint failures occasional | 4 — PDF success rate ≥ 95%; includes judge score when available; CE branding applied |
| **Budget visibility** | Tenant admins can see cumulative spend, monthly budget cap, and % utilization from the portal | Portal `/billing` or usage page; `GET /api/usage` returns `monthly_budget_usd` and `budget_pct_used`; budget can be set from portal | 2 — cost tracked in Postgres `runs` table; no budget cap UI; no portal usage page | 4 — usage page live; budget cap settable; 80%/100% alert emails sent |
| **Run scheduling** | Users can schedule a one-time or recurring run from the portal without writing code or calling the API directly | Portal `/research` page with standing question CRUD; `StandingQuestion` table populated; APScheduler fires on schedule | 1 — no scheduling UI; no standing question model | 3 — standing question CRUD in portal; scheduler fires; no advanced recurrence UI yet |

---

## 8. Market Readiness

**Baseline category score: 2/5**

Evidence basis: tenant isolation enforced at middleware (`api/middleware/clerk_auth.py`) across all paths; Stripe billing scaffolded in portal but `/billing` is a stub; no CI eval gate on deploy; dual-write debt (`run` SQLModel + `runs` Alembic table both load-bearing); no scheduler; no customer onboarding doc.

| Criterion | Definition | Measurement Method | Baseline (2026-Q2) | Target (2026-Q4) |
|-----------|-----------|-------------------|-------------------|-----------------|
| **Tenant isolation assurance** | No run, graph node, or Pinecone record from tenant A is visible to tenant B; enforced at middleware, not per-endpoint | Integration test: create two Clerk orgs; run a protocol in each; verify `GET /api/runs` for org A never returns org B runs; Pinecone namespace check | 4 — Clerk JWT `org_slug` enforced at `clerk_auth.py`; all queries scoped; FalkorDB per-tenant graph | 5 — automated tenant isolation test in CI; no regressions in 2 quarters |
| **Billing surface** | Clerk Billing portal component embedded; tenants can view and manage Stripe subscription without developer intervention | Portal `/billing` page renders Clerk Billing component; test with a Stripe test-mode subscription | 2 — Stripe scaffolded; `/billing` route is stub | 4 — `/billing` live with Clerk component; subscription state visible; plan upgrade works |
| **CI eval gate** | Every deploy to Railway runs a smoke eval suite; a score drop > 1 point from baseline blocks the deploy | `.github/workflows/` or Railway deploy hook; `smoke-tests/eval-baseline.json` committed; CI log shows eval step | 1 — CI runs `pytest -m "not integration"` only; no eval gate | 3 — eval gate on P03 Q1.1; baseline JSON in repo; Railway deploy blocked on regression |
| **Dual-write debt resolution** | A single table is the authoritative run record; the other is derived via view or deprecated | Inspect `api/models.py` and `ce-db/alembic/` — one `run` schema; no dual-write in `api/runner.py` | 2 — `run` SQLModel + `runs` Alembic table both load-bearing; write failure to either is silent (Risk R1 in SYSTEMS-ASSESSMENT) | 4 — one source of truth designated; migration executed; dual-write removed from `runner.py` |
| **Admin console** | CE admins can view all tenant run counts, costs, and last-active dates from portal without DB console access | Portal `/admin` page (gated to `org:admin` Clerk role for `cardinal-element` org); reads from `GET /api/usage?all_tenants=true` | 1 — `/admin` route is stub; requires Railway DB console for tenant visibility | 3 — admin page live; tenant list with run counts and costs; last-active date shown |
| **Customer scheduler access** | Paying customers can create standing questions from the portal and receive delta email notifications when scheduled runs complete | Portal `/research` page CRUD; `StandingQuestion.notify_email` triggers email via Resend or SMTP; test with a live Clerk org | 1 — no standing question concept; no scheduler; no email notifications | 3 — standing question CRUD and scheduler live; email notification on run completion |

---

## Scoring Log

Score each category quarterly. Add a row per session; do not edit prior rows.

| Date | Q&R | Cost | Routing | Orch. | Knowledge | Agent Factory | Usability | Market | Scorer | Notes |
|------|-----|------|---------|-------|-----------|---------------|-----------|--------|--------|-------|
| 2026-06-11 | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 | 1.0 | 3.0 | 2.0 | Claude/Scott — initial baseline | Tier 1 caching in working tree counts toward Cost; not yet verified in production. Tenant isolation evidence strong enough for Market 4 on that criterion, but other Market criteria at 1–2 pull category average to 2. |

---

*Next score due: 2026-09-30 (Q3 close). Priority signals for mid-quarter re-score: Tier 1 merge to production, circuit breaker verification, router allowlist expansion.*
