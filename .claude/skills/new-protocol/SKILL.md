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
3. **`prompts.py`** — string constants only. When `protocols/prompt_fragments.py` exists, prefer `from protocols.prompt_fragments import JSON_ENVELOPE, CIN_SCALE, PROHIBITED_HEADER` over redeclaring.
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

## After scaffolding

1. Add the protocol to `protocols/registry.py` so the router can find it.
2. Add its capability to `p0a_reasoning_router`'s prompt if you want it routable.
3. Add a smoke test: run `python -m protocols.{id}.run -q "test question" -a ceo cfo` and confirm it persists a run.
4. Verify Langfuse tracing appears (if configured).
5. Add a Mermaid diagram to `protocol-diagrams/` following the color conventions in `CLAUDE.md`.

Do NOT copy prompt boilerplate verbatim from another protocol — use `prompt_fragments.py` if it exists. If it doesn't, note that shared fragments should be extracted.
