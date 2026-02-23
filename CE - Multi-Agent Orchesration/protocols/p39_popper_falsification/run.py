"""CLI entry point for P39: Popper Falsification Gate.

Usage:
    python -m protocols.p39_popper_falsification.run \
        --recommendation "We should expand into the European market" \
        --question "How should we grow internationally?" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import FalsificationOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the Falsification result."""
    print("\n" + "=" * 70)
    print("POPPER FALSIFICATION GATE")
    print("=" * 70)

    print(f"\nRecommendation: {result.recommendation}\n")

    print("-" * 40)
    print("FALSIFICATION CONDITIONS")
    print("-" * 40)
    for i, c in enumerate(result.conditions, 1):
        status = "ACTIVATED" if c.get("activated") else "NOT ACTIVATED"
        print(f"\n  {i}. [{status}] {c['condition']}")
        if c.get("reasoning"):
            print(f"     Reasoning: {c['reasoning']}")

    print("\n" + "=" * 70)
    verdict_label = {
        "SURVIVES": "SURVIVES — Recommendation withstands scrutiny",
        "WEAKENED": "WEAKENED — Proceed with caution",
        "FALSIFIED": "FALSIFIED — Recommendation should be reconsidered",
    }.get(result.verdict, result.verdict)
    print(f"VERDICT: {verdict_label}")
    print("=" * 70)
    if result.verdict_reasoning:
        print(f"\n{result.verdict_reasoning}")
    if result.synthesis:
        print(f"\n--- Synthesis ---\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P39: Popper Falsification Gate")
    parser.add_argument("--recommendation", "-r", required=True, help="The recommendation to test")
    parser.add_argument("--question", "-q", default="", help="Original question for context")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = FalsificationOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Popper Falsification Gate with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.recommendation, args.question))

    if args.json:
        print(json.dumps({
            "recommendation": result.recommendation,
            "conditions": result.conditions,
            "verdict": result.verdict,
            "verdict_reasoning": result.verdict_reasoning,
            "synthesis": result.synthesis,
        }, indent=2, default=str))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
