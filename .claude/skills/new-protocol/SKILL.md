---
name: new-protocol
description: Scaffold a new coordination protocol in CE - Multi-Agent Orchestration. Use when the user asks to add, create, or scaffold a protocol (e.g. "add protocol P58", "new coordination protocol for X").
---

# New Protocol Scaffold

Every protocol is a self-contained package under `CE - Multi-Agent Orchestration/protocols/p{NN}_{descriptor}/` (kebab → snake, e.g. `p58_futarchy`). Copy the shape of an existing protocol in the same family — `p53_contract_net` for decentralized, `p28_six_hats` for a simple staged protocol, `p04_multi_round_debate` for multi-round.

## Required files

| File | Contract |
|------|----------|
| `__init__.py` | Export the orchestrator class and result dataclass |
| `capability.yaml` | `protocol_id`, `name`, `category`, `problem_types`, `cost_tier`, `min_agents`/`max_agents`, `supports_rounds`, `description`, `when_to_use`, optional `stages:` DAG with `depends_on` and `recommended_agents`. **This file IS the registration** — the API manifest scans for it; there is no separate registry edit. |
| `orchestrator.py` | Async class with `async def run(self, question) -> {Name}Result`. Accept `thinking_model` (default `claude-opus-4-7`) and `orchestration_model` (default `claude-haiku-4-5-20251001`). Decorate with `@trace_protocol` from `protocols/langfuse_tracing.py`. Dispatch LLM calls through `protocols/llm.py:agent_complete()` — never raw SDK calls. |
| `prompts.py` | All prompt templates as string constants — no inline prompts in the orchestrator |
| `run.py` | argparse CLI: `-q/--question`, `-a/--agents`, `--thinking-model`, `--orchestration-model`, `--mode` (+ `--rounds/-r` if multi-round), `print_result()` |

## Checklist after scaffolding

1. Agents come from `build_agents()` / `agent_provider.py` — production mode is the default; never hard-code research dicts.
2. Result dataclass named `{Name}Result`; persist raw output via the existing persistence layer (`protocols/persistence.py` is called by the runner — don't reinvent).
3. Add the protocol to the taxonomy list in `CE - Multi-Agent Orchestration/CLAUDE.md` (the ONLY place the taxonomy lives).
4. Run `python scripts/check-doc-drift.py --fs-only` from the repo root — every doc count must match the new `capability.yaml` total.
5. Smoke test: `python -m protocols.pNN_name.run -q "test question" -a ceo cfo --mode research` (research mode only for the smoke test; verify production separately).
6. Add a test in `tests/` following `tests/test_orchestrator_smoke.py`.
