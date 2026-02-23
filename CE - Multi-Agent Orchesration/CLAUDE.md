# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The **Coordination Lab** is Cardinal Element's multi-agent research program. It contains 48 implemented coordination protocols (P0a-c, P3-P47) plus a shared 56-agent registry, 34 benchmark questions across 8 problem types, and an evaluation harness. The goal is to empirically validate these protocols across problem types, then build an adaptive router that selects the optimal protocol for any strategic question.

## Running Protocols

Every protocol is a standalone Python module. Only dependency: `anthropic` (see `requirements.txt`).

```bash
# Run any protocol
python -m protocols.p06_triz.run -q "Should we expand into Europe?" -a ceo cfo cto
python -m protocols.p04_multi_round_debate.run -q "Should we expand?" -a ceo cfo cto --rounds 3
python -m protocols.p05_constraint_negotiation.run -q "Should we expand?" -a ceo cfo cto --rounds 2

# All protocols accept: --question/-q, --agents/-a, --agent-config, --thinking-model, --orchestration-model
# Multi-round protocols (P4, P5, P17, P18, etc.) also accept: --rounds/-r

# Run evaluation harness against benchmark questions
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto --dry-run
```

## Protocol Architecture (the pattern every protocol follows)

Each protocol lives in `protocols/p{NN}_{name}/` with these files:

| File | Purpose |
|------|---------|
| `__init__.py` | Exports the orchestrator class and result dataclass |
| `orchestrator.py` | The core logic: an async class with `run(question) -> *Result` |
| `prompts.py` | All LLM prompt templates as string constants |
| `run.py` | CLI entry point with argparse, `BUILTIN_AGENTS` dict, `print_result()` |
| `constraints.py` | Only in P5 — self-contained constraint extraction |

**Agent contract**: Agents are `{"name": str, "system_prompt": str}` dicts. No classes, no inheritance. Any agent collection works.

**Model strategy**: Two model tiers passed to orchestrators:
- `thinking_model` (default: `claude-opus-4-6`) — for agent reasoning, synthesis, creative stages
- `orchestration_model` (default: `claude-haiku-4-5-20251001`) — for mechanical stages (dedup, ranking, extraction, classification)

**Async throughout**: All orchestrators use `anthropic.AsyncAnthropic()` and `asyncio.gather()` for parallel agent queries. CLIs wrap with `asyncio.run()`.

**Result pattern**: Each protocol defines dataclasses for its output (e.g., `TRIZResult`, `DebateResult`). No persistence — results are returned in-memory and printed by `run.py`.

## Key Documents

- `The Coordination Lab *.md` — Master research spec: problem type taxonomy, protocols, evaluation rubrics, benchmark questions
- `benchmark-questions.json` — 34 structured benchmark questions across 8 problem types (referenced by `scripts/evaluate.py`)
- `protocols/agents.py` — Shared registry of 56 agents across 14 categories (supports `@category` group syntax)
- `protocol-diagrams/` — Mermaid diagrams for protocols (summary flows + detailed mechanics)
- `smoke-tests/` — Saved outputs from protocol runs for regression reference

## Protocol Taxonomy

- **P0a-P0c**: Meta-Protocols — Reasoning Router, Skip Gate, Tiered Escalation
- **P3-P5**: Baselines — Parallel Synthesis, Multi-Round Debate, Constraint Negotiation
- **P6-P15**: Liberating Structures — TRIZ, Wicked Questions, Min Specs, Troika, HSR, DAD, 25/10, Ecocycle, 1-2-4-All, What/So What/Now What
- **P16-P18**: Intelligence Analysis — ACH, Red/Blue/White Team, Delphi Method
- **P19-P21**: Game Theory — Vickrey Auction, Borda Count, Interests-Based Negotiation
- **P22-P23**: Org Theory — Sequential Pipeline, Cynefin Probe-Sense-Respond
- **P24-P25**: Systems Thinking — Causal Loop Mapping, System Archetype Detection
- **P26-P27**: Design Thinking — Crazy Eights, Affinity Mapping
- **P28-P47**: Wave 2 Research — Six Hats, PMI, Llull, Wittgenstein, Tetlock, Evaporation Cloud, CRT, Satisficing, Peirce, Hegel, Klein, Popper, Boyd OODA, Duke, Aristotle, Leibniz, Kant, Whitehead, Incubation, Polya

P1 (Single Agent) and P2 (Single + Context) are trivial single-call patterns with no orchestrator — they live in the C-Suite codebase only.

## Diagram Conventions

When creating or editing Mermaid diagrams in `protocol-diagrams/`:
- `([Text]):::agent` — Agent nodes | `[Text]:::stage` — Processing stages | `{Text}:::decision` — Decision gates
- Category colors: Meta `#607D8B` | Baselines `#4A90D9` | Liberating Structures `#9B59B6` | Intelligence `#E74C3C` | Game Theory `#F39C12` | Org Theory `#1ABC9C` | Systems `#2ECC71` | Design `#E91E63`

## Important Context

- The adaptive router uses **Cynefin framework** as meta-logic (Clear/Complicated/Complex/Chaotic → different protocol families)
- Protocols are **agent-agnostic orchestration patterns** — not tied to C-Suite or any specific agent collection
- "C-Suite" refers to Cardinal Element's separate multi-agent product (`/Users/scottewalt/Documents/CE - C-Suite/`) with role-specific agents (CEO, CFO, CTO, CMO, COO, CPO, CRO)
