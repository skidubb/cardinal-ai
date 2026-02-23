"""CLI entry point for P33: Goldratt Evaporation Cloud Protocol.

Usage:
    python -m protocols.p33_evaporation_cloud.run \
        --question "We need speed but also need quality" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import EvaporationCloudOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result, as_json=False):
    """Pretty-print the Evaporation Cloud result."""
    if as_json:
        print(json.dumps({
            "question": result.question,
            "cloud": result.cloud,
            "assumptions": result.assumptions,
            "injection_point": result.injection_point,
            "solution": result.solution,
            "synthesis": result.synthesis,
        }, indent=2))
        return

    print("\n" + "=" * 70)
    print("EVAPORATION CLOUD RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("THE CLOUD")
    print("-" * 40)
    c = result.cloud
    print(f"\n  Objective:      {c.get('objective', 'N/A')}")
    print(f"  Requirement A:  {c.get('requirement_a', 'N/A')}")
    print(f"  Requirement B:  {c.get('requirement_b', 'N/A')}")
    print(f"  Prerequisite A: {c.get('prerequisite_a', 'N/A')}")
    print(f"  Prerequisite B: {c.get('prerequisite_b', 'N/A')}")

    print("\n" + "-" * 40)
    print("HIDDEN ASSUMPTIONS BY ARROW")
    print("-" * 40)
    for arrow, assumptions in result.assumptions.items():
        print(f"\n  {arrow}:")
        for i, a in enumerate(assumptions, 1):
            print(f"    {i}. {a}")

    print("\n" + "-" * 40)
    print("INJECTION POINT")
    print("-" * 40)
    print(f"\n  Weakest assumption: {result.injection_point}")
    print(f"\n  Solution: {result.solution}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P33: Goldratt Evaporation Cloud Protocol")
    parser.add_argument("--question", "-q", required=True, help="The conflict or contradiction to dissolve")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = EvaporationCloudOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Evaporation Cloud with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
