"""CLI entry point for P40: Boyd OODA Rapid Cycle Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p40_boyd_ooda.run \
        --question "Competitor just launched a free tier — what do we do?" \
        --agents ceo cfo cto cmo

    # With custom agent definitions
    python -m protocols.p40_boyd_ooda.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import OODAOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the OODA result."""
    print("\n" + "=" * 70)
    print("BOYD OODA RAPID CYCLE RESULTS")
    print("=" * 70)

    print(f"\nSituation: {result.question}")
    print(f"Cycles completed: {len(result.cycles)}\n")

    for cycle in result.cycles:
        print("-" * 40)
        print(f"CYCLE {cycle['cycle_number']}")
        print("-" * 40)

        print(f"\n  OBSERVE:")
        for line in cycle["observe"].split("\n"):
            print(f"    {line}")

        print(f"\n  ORIENT:")
        for line in cycle["orient"].split("\n"):
            print(f"    {line}")

        print(f"\n  DECIDE:")
        for line in cycle["decide"].split("\n"):
            print(f"    {line}")

        print(f"\n  ACT:")
        for line in cycle["act"].split("\n"):
            print(f"    {line}")

    print("\n" + "=" * 70)
    print("FINAL ACTION")
    print("=" * 70)
    print(f"\n{result.final_action}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P40: Boyd OODA Rapid Cycle Protocol")
    parser.add_argument("--question", "-q", required=True, help="The situation to analyze")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--cycles", "-c", type=int, default=2, help="Number of OODA loops (default: 2)")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = OODAOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        num_cycles=args.cycles,
    )

    print(f"Running Boyd OODA Rapid Cycle with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    print(f"Cycles: {args.cycles}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "cycles": result.cycles,
            "final_action": result.final_action,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
