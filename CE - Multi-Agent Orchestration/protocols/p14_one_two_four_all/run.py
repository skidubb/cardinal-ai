#!/usr/bin/env python3
"""CLI entry-point for P14: 1-2-4-All protocol."""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import textwrap

from .orchestrator import AgentSpec, OneTwoFourAllOrchestrator, OneTwoFourAllResult
from protocols.agents import build_agents


def print_result(result: OneTwoFourAllResult) -> None:
    """Pretty-print the full 1-2-4-All result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P14: 1-2-4-ALL RESULT")
    print(sep)
    print(f"\nQuestion: {result.question}\n")

    # Stage 1 — Solo
    print(f"{sep}\nSTAGE 1 — SOLO IDEATION\n{sep}")
    for name, text in result.solo_outputs.items():
        print(f"\n--- {name} ---")
        print(textwrap.fill(text, width=88))

    # Stage 2 — Pairs
    print(f"\n{sep}\nSTAGE 2 — PAIR MERGES\n{sep}")
    for i, pair in enumerate(result.pair_outputs, 1):
        label = ", ".join(pair["names"])
        print(f"\n--- Pair {i} ({label}) ---")
        print(textwrap.fill(pair["text"], width=88))

    # Stage 3 — Quads
    print(f"\n{sep}\nSTAGE 3 — QUAD MERGES\n{sep}")
    for i, quad in enumerate(result.quad_outputs, 1):
        label = ", ".join(quad["names"])
        print(f"\n--- Quad {i} ({label}) ---")
        print(textwrap.fill(quad["text"], width=88))

    # Stage 4 — Final synthesis
    print(f"\n{sep}\nSTAGE 4 — FINAL SYNTHESIS\n{sep}")
    print(result.final_synthesis)

    # Stats
    print(f"\n{sep}\nSTATS\n{sep}")
    print(f"Elapsed: {result.elapsed_seconds}s")
    for model, count in result.model_calls.items():
        print(f"  {model}: {count} calls")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="P14: 1-2-4-All — Progressive merging protocol",
    )
    parser.add_argument("--question", "-q", required=True, help="Strategic question to explore")
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help="Agent keys to include (default: ceo cfo cto cmo)",
    )
    parser.add_argument("--thinking-budget", type=int, default=10_000, help="Extended thinking budget")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agent_dicts = build_agents(args.agents, mode=args.mode)
    agents = [AgentSpec(name=a["name"], system_prompt=a["system_prompt"]) for a in agent_dicts]

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P14_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P14_DEF.protocol_id}, stages: {[s.name for s in P14_DEF.stages]}")
            return

        client = make_client(protocol_id="p14_one_two_four_all", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P14_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("1-2-4-ALL RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = OneTwoFourAllOrchestrator(agents=agents, thinking_budget=args.thinking_budget)
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p14_one_two_four_all",
            question=args.question,
            agent_keys=[a['name'] for a in agents],
            result=result,
            trace_id=getattr(result, '_langfuse_trace_id', None) or get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
