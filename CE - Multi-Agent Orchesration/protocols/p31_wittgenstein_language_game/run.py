"""CLI entry point for P31: Wittgenstein Language Game Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p31_wittgenstein_language_game.run \
        --question "Should we pivot from services to product?" \
        --agents ceo cfo cto cmo

    # With custom agent definitions
    python -m protocols.p31_wittgenstein_language_game.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import LanguageGameOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the Language Game result."""
    print("\n" + "=" * 70)
    print("WITTGENSTEIN LANGUAGE GAME RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("VOCABULARY ASSIGNMENTS")
    print("-" * 40)
    for name, domain in result.vocabulary_assignments.items():
        print(f"  {name}: {domain}")

    print("\n" + "-" * 40)
    print("REFRAMINGS")
    print("-" * 40)
    for name, reframing in result.reframings.items():
        domain = result.vocabulary_assignments.get(name, "unknown")
        print(f"\n  === {name} ({domain}) ===")
        print(f"  {reframing[:500]}{'...' if len(reframing) > 500 else ''}")

    print("\n" + "-" * 40)
    print("RANKING & ANALYSIS")
    print("-" * 40)
    print(f"\n{result.ranking}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P31: Wittgenstein Language Game Protocol")
    parser.add_argument("--question", "-q", required=True, help="The problem to reframe")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = LanguageGameOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Wittgenstein Language Game with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "vocabulary_assignments": result.vocabulary_assignments,
            "reframings": result.reframings,
            "ranking": result.ranking,
            "best_reframe": result.best_reframe,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
