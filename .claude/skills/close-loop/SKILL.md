---
name: close-loop
description: Wire a write-only telemetry surface into a reader that changes future behavior. Use when the user says "close the P45 loop", "make the router adaptive", "feed evaluator scores back", or similar. The Cardinal Element system LOGS a lot but doesn't LEARN — this skill closes one loop at a time.
---

# /close-loop

Cardinal Element has multiple write surfaces (Postgres `runs`, Pinecone memory, DuckDB `ExperienceLog`, Langfuse dataset scores, P45 `weights.json`) but few readers that change behavior. This skill helps close one loop cleanly.

## Menu of open loops (as of last audit)

| Loop | Writer | Should be read by | Status |
|---|---|---|---|
| **P45 weights → router** | `p45_whitehead_weights` → `~/.coordination-lab/weights.json` | `p0a_reasoning_router` | **OPEN** — no cross-import exists |
| **Evaluator scores → weights** | CE-Evals judge → `assessments/` + Langfuse | `p45_whitehead_weights.record()` | **OPEN** — `record()` requires human `--score` today |
| **FeedbackStore → SdkAgent** | `SelfEvaluator` writes | `SdkAgent._build_system_prompt` should retrieve exemplars | **OPEN** — `retrieve_exemplars()` has zero non-test callers |
| **Runs table → router** | `persist_run()` writes | `p0a_reasoning_router` reads history for problem-type | **OPEN** — router uses static YAML only |

## The default close: P45 → P0a

This is the highest-leverage loop. Ten lines in `p0a` will convert the advertised "adaptive router" from roadmap to real.

**Where to change:**
- `CE - Multi-Agent Orchestration/protocols/p0a_reasoning_router/orchestrator.py` — after Phase 3 (routing decision), read weights and bias `recommended_protocol`.
- `CE - Multi-Agent Orchestration/protocols/p45_whitehead_weights/` — expose a `get_weight(agent_key, protocol_id, problem_type) -> float` helper if it doesn't already.

**Storage move (optional but recommended):**
- Move `weights.json` from `~/.coordination-lab/` to Postgres via `ce-db`. Table: `router_weights (agent_key, protocol_id, problem_type, weight, sample_count, updated_at)`. Migrates the loop from per-user local state to shared state.

## The pattern for any loop

1. **Find the writer.** Grep for the write call. Note what it writes and where.
2. **Find the natural reader.** Which module makes a decision that this data would improve? Usually a router, a selector, or a system-prompt builder.
3. **Add the read.** Idempotent, best-effort — if the store is empty or unavailable, fall back to today's behavior. Never break the run.
4. **Prove the loop.** Write a test that (a) records a fake score, (b) runs the reader, (c) asserts the reader's output changed.
5. **Log the change.** Emit a Langfuse span `loop:{name}` on both write and read so you can watch the loop close in traces.

## Post-check

Run:

```bash
cd "CE - Multi-Agent Orchestration"
python -m protocols.p0a_reasoning_router.run -q "sample question"
# Then run the same question a second time and confirm the recommendation
# shifts if you've recorded a score in between.
```

Do NOT close a loop by making the reader depend on a store that isn't guaranteed to exist. Always fall back gracefully.
