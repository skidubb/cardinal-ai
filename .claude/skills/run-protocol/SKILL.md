---
name: run-protocol
description: Correctly run a coordination protocol from CE - Multi-Agent Orchestration (venv, production mode, module names). Use whenever executing, smoke-testing, or evaluating a protocol run.
---

# Run a Protocol

## Non-negotiables

1. **Always production mode** for any run whose output will be read, scored, or shown. Production is the default; NEVER pass `--mode research` or set `AGENT_MODE=research` except for throwaway smoke tests — research mode strips agents to bare dicts (no tools, no memory) and any eval scores from it are invalid.
2. **If production mode fails to import Agent Builder, say so explicitly** — check `/api/health` (`agent_builder` field) or the `DEGRADED:` log lines. Do not silently continue.
3. **Activate the project venv first**: `cd "CE - Multi-Agent Orchestration" && source venv/bin/activate`. If imports hang at 0% CPU, the venv is iCloud-evicted — force-materialize with `find venv/lib -name "*.py" -o -name "*.so" | xargs -P 8 -n 50 cat > /dev/null`.

## Invocation

```bash
python -m protocols.p{NN}_{name}.run -q "question" -a ceo cfo cto
# multi-round protocols add: --rounds/-r N
# model overrides: --thinking-model / --orchestration-model
```

Gotchas:
- Module names don't always match shorthand — check with Glob first (`p29_pmi_enumeration` not `p29_pmi`, `p32_tetlock_forecast` not `p32_tetlock`).
- P29 PMI is single-LLM — no `-a` flag. P45 Whitehead Weights is a meta-protocol with special args.
- When chaining protocols, each protocol's output must enrich the next protocol's input — never feed the same raw question to every step.
- Before debugging a hang, rule out external causes first: Anthropic status/quota/529s, then iCloud venv eviction, then code.

## Evaluation harness

```bash
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
```
