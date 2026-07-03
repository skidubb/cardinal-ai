---
name: new-protocol
description: Scaffold a new Coordination Lab protocol (orchestrator.py, prompts.py, run.py, README.md, capability.yaml, protocol_def.py). Use when the user asks to create a new protocol like "add p53_...", "scaffold a new protocol", or "start a stigmergy protocol".
---

# /new-protocol

Scaffolds a new protocol under `CE - Multi-Agent Orchestration/protocols/` following the canonical five-file pattern.

## Arguments

The user typically says something like: `/new-protocol p53_stigmergy category=Systems`.

Parse:
- **id** — `p{NN}_{descriptor}` (e.g. `p53_stigmergy`). Kebab case for descriptor, snake_case since it's a Python module. Increment from the highest existing `pNN`.
- **category** — one of: Meta, Baselines, Liberating Structures, Intelligence Analysis, Game Theory, Org Theory, Systems, Design, Wave 2 Research, Walk, Composite.
- **coordination** (optional) — Centralized / Decentralized / Hybrid.

## What you must produce

Create these files under `CE - Multi-Agent Orchestration/protocols/{id}/`:

1. **`__init__.py`** — exports the orchestrator class and result dataclass.
2. **`orchestrator.py`** — async class with `run(question) -> {Name}Result`. Uses `@trace_protocol("{id}")` decorator, `anthropic.AsyncAnthropic()`, `THINKING_MODEL` for reasoning, `ORCHESTRATION_MODEL` for mechanical steps. Import from `protocols.llm`, `protocols.langfuse_tracing`, `protocols.config`.
3. **`prompts.py`** — string constants only. Prefer `from protocols.prompt_fragments import JSON_ONLY_INSTRUCTION, CIN_SCALE_SCORING, PROHIBITED_HEADER, agent_framing` over redeclaring boilerplate. The fragment library is the single source of truth for JSON envelopes, C/I/N scales, prohibition headers, and agent framing.
4. **`run.py`** — CLI with argparse, `BUILTIN_AGENTS` dict, `print_result()`, calls `persist_run()` from `protocols.persistence`.
5. **`capability.yaml`** — metadata read by `p0a_reasoning_router`:
   ```yaml
   id: {id}
   name: <Human name>
   category: <Category>
   coordination: <Centralized|Decentralized|Hybrid>
   problem_types: [<types this protocol suits>]
   agent_count: {min, max, recommended}
   rounds: {default, max}
   cost_tier: <low|medium|high>
   ```
6. **`README.md`** — mechanics, usage examples, arguments table, output structure. Follow the pattern of `p18_delphi_method/README.md`.

## Canonical templates to copy from

- **Baseline**: `p03_parallel_synthesis/` — parallel + synthesizer
- **Multi-round**: `p04_multi_round_debate/` — sequential rounds
- **Decentralized (voting)**: `p20_borda_count/` — vote aggregation
- **Decentralized (auction)**: `p19_vickrey_auction/` — sealed-bid math
- **Systems (structured output)**: `p24_causal_loop_mapping/` — graph algorithm
- **Composite (blackboard)**: `airport_5g_pipeline/` — uses `ProtocolDef` + `orchestrator_loop.py`

Pick the closest template and adapt.

## Per-agent prompt assembly — use scoping

Every new protocol should build per-agent prompts through `protocols.scoping.scoped_prompt` so agents only see context matching their `context_scope` (financial, technical, market, operational, strategic, hr, all). Ad-hoc `f"{TASK}\n\n{full_context_blob}"` concatenation is a regression.

```python
from protocols.scoping import scoped_prompt

# In your parallel stage:
prompt = scoped_prompt(
    agent,
    TASK_PROMPT.format(question=question),
    shared_context=blackboard.blocks() if use_blackboard else None,
)
response = await agent.chat(prompt)
```

## After scaffolding

1. Add the protocol to `protocols/registry.py` so the router can find it.
2. Add its capability to `p0a_reasoning_router`'s prompt if you want it routable.
3. Add a smoke test: run `python -m protocols.{id}.run -q "test question" -a ceo cfo` and confirm it persists a run.
4. Verify Langfuse tracing appears (if configured).
5. Confirm auto-scoring flows (check `~/.coordination-lab/weights.json` grew a record).
6. Add a Mermaid diagram to `protocol-diagrams/` following the color conventions in `CLAUDE.md`.

Do NOT copy prompt boilerplate verbatim from another protocol — always route through `prompt_fragments.py`.
