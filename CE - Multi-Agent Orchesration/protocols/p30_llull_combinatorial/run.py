"""CLI entry point for P30: Llull Combinatorial Association Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p30_llull_combinatorial.run \
        --question "How should we price our AI product?" \
        --agents ceo cfo cto

    # With custom agent definitions
    python -m protocols.p30_llull_combinatorial.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import CombinatorialOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the Llull Combinatorial result."""
    print("\n" + "=" * 70)
    print("LLULL COMBINATORIAL ASSOCIATION RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("CONCEPT DISKS")
    print("-" * 40)
    for i, disk in enumerate(result.disks):
        name = disk.get("category_name", f"Disk {chr(65 + i)}")
        elements = ", ".join(disk.get("elements", []))
        print(f"  Disk {chr(65 + i)} ({name}): {elements}")

    print("\n" + "-" * 40)
    print("COMBINATIONS (exhaustive)")
    print("-" * 40)
    print(f"\n{result.combinations}")

    print("\n" + "-" * 40)
    print(f"EVALUATIONS ({result.non_obvious_count}/{result.total_count} non-obvious)")
    print("-" * 40)
    print(f"\n{result.evaluations}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P30: Llull Combinatorial Association Protocol")
    parser.add_argument("--question", "-q", required=True, help="The problem or question to explore")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = CombinatorialOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Llull Combinatorial with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "disks": result.disks,
            "combinations": result.combinations,
            "evaluations": result.evaluations,
            "non_obvious_count": result.non_obvious_count,
            "total_count": result.total_count,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
