---
phase: 1
plan: 3
title: "Migrate Orchestration cost tracker to ce-shared and update roadmap"
wave: 2
depends_on: [1]
requirements: [PRIC-06, PRIC-08]
files_modified:
  - CE - Multi-Agent Orchestration/protocols/cost_tracker.py
  - CE - Multi-Agent Orchestration/protocols/llm.py
  - CE - Multi-Agent Orchestration/requirements.txt
  - .planning/ROADMAP.md
autonomous: true
---

# Plan 3: Migrate Orchestration cost tracker to ce-shared and update roadmap

## Objective
Remove all local pricing definitions from Orchestration's `cost_tracker.py`, replace them with imports from `ce_shared.pricing`, ensure the `_compute_cost` import chain from `llm.py` remains stable, and update the ROADMAP.md success criteria with verified pricing values.

## must_haves
- `_PRICING` dict, `_CACHE_READ_MULTIPLIER`, and `_price_for_model()` are no longer defined in Orchestration's `cost_tracker.py` — replaced by ce_shared imports
- `_compute_cost()` function still exists in `protocols.cost_tracker` and is importable from `protocols/llm.py` line 171 — it becomes a thin wrapper calling `ce_shared.pricing.cost_for_model()`
- `ce-shared` is listed in Orchestration's `requirements.txt` using the `@ file:../ce-shared` pattern (matching how `ce-db` is referenced)
- `protocols/llm.py` continues to work without changes (or with minimal import path updates if `_compute_cost` signature changes)
- `ProtocolCostTracker` class, `_ModelStats`, `_AgentStats` are NOT modified
- ROADMAP.md Phase 1 success criteria pricing values are corrected to match verified prices from ce-shared
- `from ce_shared.pricing import MODEL_PRICING` works in the Orchestration venv

<tasks>
<task id="1">
Add `ce-shared @ file:../ce-shared` to `CE - Multi-Agent Orchestration/requirements.txt`, following the existing `ce-db @ file:../ce-db` pattern. Run `pip install -r "CE - Multi-Agent Orchestration/requirements.txt"` to verify it resolves.
</task>
<task id="2">
In `CE - Multi-Agent Orchestration/protocols/cost_tracker.py`:
- Delete the `_PRICING` dict (lines ~26-38)
- Delete `_CACHE_READ_MULTIPLIER` constant (lines ~40-41)
- Delete `_price_for_model()` function (lines ~43-52)
- Add import at top: `from ce_shared.pricing import cost_for_model, get_pricing`
</task>
<task id="3">
Rewrite `_compute_cost()` function to be a thin wrapper around `cost_for_model()`. Current signature: `_compute_cost(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0) -> float`. Map its parameters to `cost_for_model(model, input_tokens, output_tokens, cache_read_tokens=cache_read_tokens)`. Keep the function name and its location in `protocols/cost_tracker.py` so that the import in `protocols/llm.py` line 171 remains valid.
</task>
<task id="4">
Verify `protocols/llm.py` line 171 (`from protocols.cost_tracker import _compute_cost`) still works by running: `cd "CE - Multi-Agent Orchestration" && python -c "from protocols.cost_tracker import _compute_cost; print(_compute_cost('claude-opus-4-6', 1000, 1000))"`. If the import fails, fix it.
</task>
<task id="5">
Verify no local pricing data remains: grep Orchestration's `cost_tracker.py` for `_PRICING`, `_price_for_model`, `_CACHE_READ_MULTIPLIER` definitions. Only imports should remain.
</task>
<task id="6">
Update `.planning/ROADMAP.md` Phase 1 success criteria (line 15) to replace the incorrect mixed pricing values ("Opus $5/$25, Sonnet $3/$15, Haiku $0.80/$4.00") with the correct verified values from ce-shared. The exact values depend on Plan 1 task 3 verification results.
</task>
<task id="7">
Run a quick smoke test: `cd "CE - Multi-Agent Orchestration" && python -c "from protocols.cost_tracker import ProtocolCostTracker; t = ProtocolCostTracker(); t.track('claude-opus-4-6', 1000, 500, 0); print(t.summary())"`. Verify the cost is non-zero and uses correct pricing.
</task>
</tasks>

## Verification
1. `grep -n "_PRICING\s*=" "CE - Multi-Agent Orchestration/protocols/cost_tracker.py"` returns zero matches
2. `grep -n "_price_for_model" "CE - Multi-Agent Orchestration/protocols/cost_tracker.py"` returns zero matches (no definition, only ce_shared import)
3. `python -c "from protocols.cost_tracker import _compute_cost; print(_compute_cost('claude-opus-4-6', 1000, 1000))"` succeeds from the Orchestration directory
4. `python -c "from protocols.llm import agent_complete"` does not fail on the _compute_cost import
5. Orchestration's `requirements.txt` contains `ce-shared @ file:../ce-shared`
6. ROADMAP.md success criteria pricing values match ce-shared's `MODEL_PRICING`
