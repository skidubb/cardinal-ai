# Phase 3: Token Estimation & Documentation — Research

**Completed:** 2026-03-09
**Phase:** 03-token-estimation-documentation

## Research Summary

Phase 3 addresses two gaps: (1) Langfuse traces currently show 0 tokens for SDK Agent (production mode) calls because the Agent SDK only exposes `total_cost_usd` but not token counts, and (2) the `bypassPermissions` design decision in the Agent Builder SDK agent is undocumented. The core technical challenge is back-calculating token counts from USD cost using the pricing data already centralized in `ce-shared`. The budget guardrails work is straightforward — the Orchestration cost tracker already accumulates per-run cost, so adding a warn-only ceiling check is a small addition.

There are two distinct token-estimation contexts: (A) the **Orchestration research/fallback path** where `llm.py:_record_usage()` already receives real token counts from the Anthropic SDK response — these work fine and already flow to Langfuse; and (B) the **production SDK Agent path** where `agent_complete()` calls `agent.chat()` directly, bypasses `_record_usage()` entirely, and the SDK agent only knows `self.cost` (USD) with 0 tokens. The estimation function is primarily needed for path (B).

## Codebase Analysis

### ce-shared/src/ce_shared/pricing.py — Cost Formula

The `cost_for_model()` function computes cost as:

```
cost = (input_tokens * input_rate/1M)
     + (cache_read_tokens * input_rate/1M * 0.10)
     + (cache_write_tokens * input_rate/1M * 1.25)
     + (output_tokens * output_rate/1M)
if batch: cost *= 0.50
```

`get_pricing(model)` returns `(input_per_mtok, output_per_mtok)`. Unknown models default to Opus-tier `(5.00, 25.00)`.

**Exports:** `MODEL_PRICING` dict, `ModelTier` StrEnum, `get_pricing()`, `cost_for_model()`, `CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER`, `BATCH_DISCOUNT`, `PRICING_VERIFIED_DATE`.

### CE - Multi-Agent Orchestration/protocols/llm.py — Token Extraction

`_record_usage()` (lines 120-179) extracts from SDK response:
- `input_tokens = getattr(usage, "input_tokens", 0)`
- `output_tokens = getattr(usage, "output_tokens", 0)`
- `cached_tokens = getattr(usage, "cache_read_input_tokens", 0)`

These are forwarded to both `ProtocolCostTracker.track()` and `langfuse_tracing.record_generation()`.

**Critical finding:** In `agent_complete()` (line 241-243), when the agent has a `chat()` method (production SDK agents), it calls `agent.chat(user_msg)` and returns the string directly — `_record_usage()` is never called. This means:
- No token counts are recorded for production agent calls
- No Langfuse generation spans are created for production agent calls
- No cost tracker entries are created for production agent calls

The only cost info available is `agent.cost` (a float USD value) set on `SdkAgent` at line 273 of `sdk_agent.py`.

### CE - Multi-Agent Orchestration/protocols/langfuse_tracing.py — Generation Recording

`record_generation()` (lines 299-388) creates Langfuse observation spans with:
- `usage_details = {"input": input_tokens, "output": output_tokens}` (plus optional `input_cached`)
- `cost_details = {"total": cost_usd}` when cost is provided
- `metadata` includes `cached_tokens`, `generation_type` (agent vs mechanical)

It uses `start_observation(as_type="generation")` with Langfuse SDK v3 API.

### CE - Multi-Agent Orchestration/protocols/cost_tracker.py — Protocol Cost Tracking

`ProtocolCostTracker` accumulates per-run cost via `track(model, input_tokens, output_tokens, cached_tokens, agent_name)`. `_compute_cost()` is a thin wrapper that adjusts `input_tokens` semantics (subtracts cached before delegating to `cost_for_model()`).

The tracker has `total_cost` property and `summary()` method but no budget ceiling logic.

### CE - Agent Builder/src/csuite/tools/cost_tracker.py — Budget Pattern

`CostTracker` has:
- `thresholds` dict with `single_query_cost: 2.00`, `daily_spend: 10.00`, etc.
- `check_daily_budget()` returns a `CostAlert` if exceeded
- `CostAlert` dataclass with `alert_type`, `severity`, `message`, `details`
- `_check_record_anomalies()` fires alerts on high-cost queries

This pattern can be adapted for protocol-level budget guardrails.

### CE - Agent Builder/src/csuite/agents/sdk_agent.py — bypassPermissions

At line 264, `permission_mode="bypassPermissions"` is set in `ClaudeAgentOptions`. Context:
- Used when calling `claude_agent_sdk.query()` with MCP servers
- The SDK agent runs with `max_turns=15` and `cwd=project_root`
- MCP servers include Pinecone, Notion, SEC EDGAR, Pricing Calculator, GitHub Intel
- `bypassPermissions` means the agent can execute tool calls without user approval
- The `ResultMessage` returns `total_cost_usd` but no token breakdown

## Token Back-Calculation

### Formula

Given `cost_usd` and `model`, and assuming no cache or batch (the SDK doesn't report these breakdowns):

```
cost_usd = (input_tokens * input_rate/1M) + (output_tokens * output_rate/1M)
```

This is one equation with two unknowns. We need an assumption to solve it. Options:

**Option A — Assume a fixed input:output ratio.** Typical ratio for executive agent calls is roughly 5:1 (more input than output). Use a configurable ratio `r = input_tokens / output_tokens`:
```
cost = output_tokens * (r * input_rate + output_rate) / 1M
output_tokens = cost * 1M / (r * input_rate + output_rate)
input_tokens = r * output_tokens
```

**Option B — Report total cost only, estimate combined tokens.** Treat all tokens as if they were output tokens (conservative):
```
estimated_total_tokens = cost_usd * 1M / output_rate
```

**Option C — Use the `total_cost_usd` to estimate based on assumed output-only.**

**Recommendation: Option A** with a configurable ratio defaulting to 5:1. This gives the most informative estimates for Langfuse dashboards while clearly marked as `token_source: "estimated_from_cost"`.

### Where to Implement

The estimation function should live in **`ce-shared/src/ce_shared/pricing.py`** as `estimate_tokens_from_cost()`. Reasons:
- It's the inverse of `cost_for_model()` — belongs with the pricing math
- Both Agent Builder and Orchestration can use it
- Keeps the Orchestration `llm.py` and `langfuse_tracing.py` as consumers, not owners of pricing logic

### Integration Point

In `llm.py:agent_complete()`, after the production `agent.chat()` call (line 243), add:
```python
# After: return await agent.chat(user_msg)
# Change to: capture cost, estimate tokens, record usage
result = await agent.chat(user_msg)
cost_usd = getattr(agent, "cost", 0.0)
if cost_usd > 0:
    from ce_shared.pricing import estimate_tokens_from_cost
    est = estimate_tokens_from_cost(model, cost_usd)
    _record_usage_estimated(model, est, cost_usd, agent_name, token_source="estimated_from_cost")
return result
```

## Budget Guardrails

### Approach

Add a `cost_ceiling_usd` parameter to `ProtocolCostTracker`. After each `track()` call, check if `total_cost > ceiling`. If exceeded, log a warning. No hard stop per user decision.

### Config Location

Add `PROTOCOL_COST_CEILING` to root `.env` with a sensible default (e.g., `5.00`). Load via `ce_shared.env`. The ceiling applies per protocol run (not per agent, not globally).

### Implementation

Extend `ProtocolCostTracker.__init__()` to accept `cost_ceiling_usd: float | None`. In `track()`, after accumulating cost, check ceiling and log warning. The warning should include: protocol name, current cost, ceiling, model, agent.

## Documentation

### BYPASS_PERMISSIONS.md

Location: `CE - Agent Builder/docs/BYPASS_PERMISSIONS.md`

Content scope (internal developer reference):
- **What:** `permission_mode="bypassPermissions"` in `ClaudeAgentOptions`
- **Where:** `src/csuite/agents/sdk_agent.py:264`
- **Why:** SDK agents run autonomously as part of multi-agent protocols — they cannot pause for human approval per tool call. The 48 protocols in Orchestration run agents in parallel via `asyncio.gather`; blocking on approval would deadlock the system.
- **MCP servers accessed:** Pinecone (read/write), Notion (read/write), SEC EDGAR (read-only), Pricing Calculator (read-only), GitHub Intel (read-only)
- **Risk assessment:** Write access to Pinecone and Notion without approval. Mitigated by: role-based MCP mapping (only certain agents get certain servers), `max_turns=15` limit, MCP servers are custom-built with constrained operations.
- **Mitigations in place:** Role-based MCP access (`mcp_config.py`), turn limit, read-only external APIs (SEC EDGAR, BLS, Census), custom MCP servers with limited operation set.

### ce-shared/README.md

Scope: Installation, module overview (pricing + env), usage examples, development setup. No README currently exists.

## Risks & Edge Cases

1. **Zero cost from SDK.** If `agent.cost == 0.0` (e.g., SDK call fails silently or returns no cost), token estimation would produce 0 tokens. Guard: skip estimation when cost is 0, log a warning.

2. **Cache and batch pricing in estimation.** The SDK's `total_cost_usd` may include cache discounts internally, but we have no way to know. The estimation will be approximate. This is acceptable given `token_source: "estimated_from_cost"` metadata.

3. **Input:output ratio varies.** A fixed 5:1 ratio is a heuristic. Short agent responses (e.g., "I agree") would have very different ratios than deep analysis. Consider making the ratio configurable per agent role.

4. **Production agent path bypasses all recording.** Lines 241-243 of `llm.py` return immediately after `agent.chat()`. The fix requires restructuring this early-return to capture cost and call `_record_usage()` (or a new variant). This is the most impactful change.

5. **SDK response already has real tokens.** In the research/fallback path, `_record_usage()` already gets real token counts from the Anthropic SDK. The estimation should NOT overwrite real data. Guard: only estimate when `input_tokens == 0 and output_tokens == 0 and cost > 0`.

6. **Floating-point precision.** Back-calculated token counts will be floats. Round to nearest integer. Small costs may produce 0 tokens due to rounding — use `max(1, round(...))` for non-zero cost.

7. **Multi-turn SDK agents.** An SDK agent with `max_turns=15` may make multiple LLM calls. The `total_cost_usd` is the aggregate. Token estimation from the aggregate gives total tokens, not per-call. This is fine for Langfuse — one generation span per `agent.chat()` call.

## Validation Architecture

### TOKN-01: Token estimation function in ce-shared
**What to validate:**
- `estimate_tokens_from_cost(model, cost_usd)` returns dict with `input_tokens`, `output_tokens`, `token_source`
- Returns `(0, 0)` when cost is 0
- Unknown model defaults to Opus-tier pricing
- Round-trip accuracy: `cost_for_model(model, estimated_input, estimated_output)` is within 1% of original cost
- All returned token counts are non-negative integers

### TOKN-02: Production agent path records estimated tokens
**What to validate:**
- After `agent.chat()` in `llm.py`, `_record_usage` is called with estimated tokens
- `token_source: "estimated_from_cost"` metadata is present in Langfuse span
- Cost tracker receives the estimated tokens

### TOKN-03: Langfuse traces show non-zero tokens
**What to validate:**
- `record_generation()` receives non-zero `input_tokens`/`output_tokens` for production agent calls
- `usage_details` in Langfuse span has non-zero values
- Metadata includes `token_source` field

### TOKN-04: Unknown model defaults to Opus-tier
**What to validate:**
- `estimate_tokens_from_cost("unknown-model", 0.03)` uses `(5.00, 25.00)` rates
- Unit test with unknown model string

### TOKN-05: Budget guardrail warns on ceiling breach
**What to validate:**
- `ProtocolCostTracker` with `cost_ceiling_usd=1.00` logs warning when cost exceeds $1.00
- Warning includes cost, ceiling, protocol context
- Protocol run completes (not halted)
- No warning when under ceiling

### TOKN-06: Budget ceiling configurable via env
**What to validate:**
- `PROTOCOL_COST_CEILING` in `.env` is loaded
- Default value works when env var is not set
- Value propagated to `ProtocolCostTracker`

### DOCS-01: BYPASS_PERMISSIONS.md exists
**What to validate:**
- File exists at `CE - Agent Builder/docs/BYPASS_PERMISSIONS.md`
- Contains: what, where, why, risk assessment, mitigations
- References actual line in `sdk_agent.py`

### DOCS-02: ce-shared/README.md exists
**What to validate:**
- File exists at `ce-shared/README.md`
- Contains: installation instructions, module descriptions, usage examples
- Import examples are copy-pasteable and correct

## RESEARCH COMPLETE
