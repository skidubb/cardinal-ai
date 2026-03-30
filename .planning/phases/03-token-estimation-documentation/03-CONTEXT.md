# Phase 3: Token Estimation & Documentation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Back-calculate token counts from SDK cost data using shared pricing, add budget guardrails for protocol runs, and document the `bypassPermissions` design decision. Token estimation fills the gap where SDK cost tracking has dollar amounts but no token counts in Langfuse traces.

</domain>

<decisions>
## Implementation Decisions

### Budget guardrails
- Warn only when a protocol run exceeds a configured cost ceiling — log the warning but let the run finish
- No hard-stop / kill behavior — avoids lost work from mid-run kills

### bypassPermissions documentation
- Internal developer reference only — not client-facing
- Audience: CE team developers working on Agent Builder
- Should explain why `bypassPermissions` is used, what risks exist, what mitigations are in place

### Claude's Discretion
- Token back-calculation approach: where the estimation logic lives (ce-shared, cost_tracker, or llm.py), precision/rounding, formula design
- How `token_source: "estimated_from_cost"` metadata is attached and propagated
- Budget guardrail config location and format (root .env, ce-shared config, per-protocol)
- ce-shared README scope and structure (usage examples, installation, module docs)
- BYPASS_PERMISSIONS.md structure and depth (risk categories, mitigation checklist)
- Whether budget ceiling applies per-run, per-agent, or globally

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ce-shared/src/ce_shared/pricing.py`: `cost_for_model()` already computes cost from tokens — back-calculation inverts this formula
- `CE - Agent Builder/src/csuite/tools/cost_tracker.py`: Has `check_daily_budget()` with thresholds and `CostAlert` dataclass — pattern to follow for protocol guardrails
- `CE - Multi-Agent Orchestration/protocols/cost_tracker.py`: `_compute_cost()` thin wrapper already bridges Orchestration's token semantics to ce-shared
- `CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py`: `record_generation()` already receives `input_tokens`, `output_tokens`, `cost_usd` and writes `usage_details` to Langfuse spans

### Established Patterns
- Token tracking: `llm.py` extracts `usage.input_tokens`/`output_tokens` from SDK response, passes to both cost_tracker and langfuse_tracing
- Cost calculation: All cost math delegated to `ce_shared.pricing.cost_for_model()`
- Langfuse v3 API: `usage_details={"input": N, "output": N}`, `cost_details` for USD amounts
- Agent Builder budget: `CostAlert` with severity levels, threshold dict in cost_tracker

### Integration Points
- `llm.py:134-159`: Where SDK response tokens are extracted — token estimation would happen here or be called from here
- `langfuse_tracing.py:record_generation()`: Already receives token counts — needs `token_source` metadata added
- `cost_tracker.py:_compute_cost()`: Thin wrapper that could also house back-calculation
- `sdk_agent.py:264`: The single `bypassPermissions` usage to document

</code_context>

<specifics>
## Specific Ideas

- User wants this phase kept light — focus on critical fixes, not over-engineering
- Estimation is the priority (Langfuse traces currently show 0 tokens)
- Budget guardrails should be simple: a configured dollar ceiling per protocol run, warn-only

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-token-estimation-documentation*
*Context gathered: 2026-03-09*
