#!/usr/bin/env python3
"""CLI entry point for P24: Causal Loop Mapping."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import CausalLoopOrchestrator, CausalLoopResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: CausalLoopResult) -> None:
    """Pretty-print the Causal Loop Mapping result."""
    print("\n" + "=" * 70)
    print("P24: CAUSAL LOOP MAPPING")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Variables
    print("-" * 40)
    print("SYSTEM VARIABLES")
    print("-" * 40)
    for v in result.variables:
        print(f"  {v.id}: {v.name}")
        print(f"      {v.description}")

    # Causal Links
    print(f"\n{'-' * 40}")
    print("CAUSAL LINKS")
    print("-" * 40)
    for link in result.causal_links:
        print(f"  {link.from_var} --({link.polarity})--> {link.to_var}")
        if link.reasoning:
            print(f"      {link.reasoning}")

    # Reinforcing Loops
    print(f"\n{'-' * 40}")
    print("REINFORCING LOOPS (amplify change)")
    print("-" * 40)
    if result.reinforcing_loops:
        for loop in result.reinforcing_loops:
            path_str = " -> ".join(loop.path) + " -> " + loop.path[0]
            print(f"  {loop.id}: {path_str}")
    else:
        print("  None detected")

    # Balancing Loops
    print(f"\n{'-' * 40}")
    print("BALANCING LOOPS (resist change)")
    print("-" * 40)
    if result.balancing_loops:
        for loop in result.balancing_loops:
            path_str = " -> ".join(loop.path) + " -> " + loop.path[0]
            print(f"  {loop.id}: {path_str}")
    else:
        print("  None detected")

    # Leverage Points
    print(f"\n{'-' * 40}")
    print("LEVERAGE POINT ANALYSIS")
    print("-" * 40)
    lp = result.leverage_points
    if lp.get("leverage_points"):
        for point in lp["leverage_points"]:
            print(f"\n  Target: {point.get('target_variable', '?')}")
            print(f"  Intervention: {point.get('intervention', '')}")
            print(f"  Affected loops: {', '.join(point.get('affected_loops', []))}")
            print(f"  Expected effect: {point.get('expected_effect', '')}")
            print(f"  Risk: {point.get('risk', '')}")
    if lp.get("system_summary"):
        print(f"\n  System Summary: {lp['system_summary']}")
    if lp.get("dominant_dynamic"):
        print(f"  Dominant Dynamic: {lp['dominant_dynamic']}")
    if lp.get("recommendation"):
        print(f"  Recommendation: {lp['recommendation']}")

    # Timings
    print(f"\n{'-' * 40}")
    print("TIMINGS")
    print("-" * 40)
    total = 0.0
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed:.1f}s")
        total += elapsed
    print(f"  total: {total:.1f}s")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P24: Causal Loop Mapping — systems thinking with feedback loop detection",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to analyze.",
    )
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys to use. Available: {', '.join(BUILTIN_AGENTS)}",
    )
    parser.add_argument(
        "--thinking-model",
        default=None,
        help="Override the thinking model (default: claude-opus-4-6).",
    )
    parser.add_argument(
        "--orchestration-model",
        default=None,
        help="Override the orchestration model (default: claude-haiku-4-5-20251001).",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=10000,
        help="Token budget for extended thinking (default: 10000).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = CausalLoopOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "variables": [
                {"id": v.id, "name": v.name, "description": v.description}
                for v in result.variables
            ],
            "causal_links": [
                {"from": l.from_var, "to": l.to_var, "polarity": l.polarity,
                 "reasoning": l.reasoning}
                for l in result.causal_links
            ],
            "reinforcing_loops": [
                {"id": lp.id, "path": lp.path, "polarities": lp.polarities}
                for lp in result.reinforcing_loops
            ],
            "balancing_loops": [
                {"id": lp.id, "path": lp.path, "polarities": lp.polarities}
                for lp in result.balancing_loops
            ],
            "leverage_points": result.leverage_points,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
