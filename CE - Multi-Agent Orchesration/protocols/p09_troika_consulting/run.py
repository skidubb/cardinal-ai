#!/usr/bin/env python3
"""CLI entry-point for P9: Troika Consulting protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import textwrap
from dataclasses import asdict

from .orchestrator import AgentSpec, TroikaOrchestrator, TroikaResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: TroikaResult) -> None:
    """Pretty-print the full Troika Consulting result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P9: TROIKA CONSULTING RESULT")
    print(sep)
    print(f"\nQuestion: {result.question}\n")

    for i, rnd in enumerate(result.rounds, 1):
        print(f"{sep}")
        print(f"ROUND {i} — Client: {rnd.client_name} | Consultants: {', '.join(rnd.consultants)}")
        print(sep)

        print(f"\n--- Phase 1: Problem Statement ({rnd.client_name}) ---")
        print(textwrap.fill(rnd.problem_statement, width=88))

        print(f"\n--- Phase 2a: Consultant 1 ({rnd.consultants[0]}) ---")
        print(textwrap.fill(rnd.consultant1_response, width=88))

        print(f"\n--- Phase 2b: Consultant 2 ({rnd.consultants[1]}) ---")
        print(textwrap.fill(rnd.consultant2_response, width=88))

        print(f"\n--- Phase 2c: Consolidated Advice ---")
        print(textwrap.fill(rnd.consolidated_advice, width=88))

        print(f"\n--- Phase 3: Client Reflection ({rnd.client_name}) ---")
        print(textwrap.fill(rnd.client_reflection, width=88))

        print(f"\n  [Round elapsed: {rnd.elapsed_seconds}s]")

    if result.final_synthesis:
        print(f"\n{sep}")
        print("FINAL SYNTHESIS")
        print(sep)
        print(result.final_synthesis)

    print(f"\n{sep}")
    print("STATS")
    print(sep)
    print(f"Total elapsed: {result.elapsed_seconds}s")
    for phase, secs in result.timings.items():
        print(f"  {phase}: {secs}s")
    for model, count in result.model_calls.items():
        print(f"  {model}: {count} calls")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="P9: Troika Consulting — Rotating client/consultant advisory protocol",
    )
    parser.add_argument("--question", "-q", required=True, help="Strategic question to explore")
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto"],
        help="Agent keys to include (min 3, default: ceo cfo cto)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    parser.add_argument("--thinking-budget", type=int, default=10_000, help="Extended thinking budget")
    args = parser.parse_args()

    agent_dicts = build_agents(args.agents)
    agents = [AgentSpec(name=a["name"], system_prompt=a["system_prompt"]) for a in agent_dicts]
    orchestrator = TroikaOrchestrator(agents=agents, thinking_budget=args.thinking_budget)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json_output:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
