"""CLI entry point for P34: Goldratt Current Reality Tree.

Usage:
    # With built-in agent roles
    python -m protocols.p34_current_reality_tree.run \
        --question "Why is our sales cycle exceeding 90 days?" \
        --agents ceo cfo coo cro

    # With custom agent definitions
    python -m protocols.p34_current_reality_tree.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import CRTOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the CRT result."""
    print("\n" + "=" * 70)
    print("CURRENT REALITY TREE RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("UNDESIRABLE EFFECTS (by agent)")
    print("-" * 40)
    for agent_name, udes in result.udes.items():
        print(f"\n  {agent_name}:")
        for line in udes.strip().split("\n"):
            print(f"    {line}")

    print("\n" + "-" * 40)
    print("CAUSAL TREE")
    print("-" * 40)
    print(f"\n{result.causal_tree}")

    print("\n" + "-" * 40)
    print("LOGIC AUDIT")
    print("-" * 40)
    print(f"\n{result.logic_audit}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P34: Goldratt Current Reality Tree")
    parser.add_argument("--question", "-q", required=True, help="The situation to analyze")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = CRTOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Current Reality Tree with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "udes": result.udes,
            "causal_tree": result.causal_tree,
            "logic_audit": result.logic_audit,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
