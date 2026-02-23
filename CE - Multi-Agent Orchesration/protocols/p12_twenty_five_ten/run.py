"""CLI entry point for P12: 25/10 Crowd Sourcing Protocol.

Usage:
    python -m protocols.p12_twenty_five_ten.run \
        --question "Rank these initiatives for a bootstrapped AI consultancy..." \
        --agents ceo cfo cto cmo coo cpo cro
"""

from __future__ import annotations

import argparse
import asyncio

from .orchestrator import TwentyFiveTenOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    print("\n" + "=" * 70)
    print("25/10 CROWD SOURCING RESULTS")
    print("=" * 70)

    print(f"\nChallenge: {result.challenge}")
    print(f"Ideas generated: {len(result.ideas)}")
    print(f"Scoring rounds: {result.scoring_rounds}")
    print(f"Total scores cast: {result.total_scores_cast}\n")

    print("-" * 40)
    print("RANKED IDEAS")
    print("-" * 40)
    for i, idea in enumerate(result.ideas):
        marker = " ★ TOP 25%" if idea.is_top_quartile else ""
        print(f"\n  #{i+1} [{idea.total_score:.0f} pts] {idea.title}{marker}")
        print(f"       Author: {idea.author}")
        print(f"       Avg: Overall={idea.avg_overall:.1f} Bold={idea.avg_boldness:.1f} Feasible={idea.avg_feasibility:.1f} Impact={idea.avg_impact:.1f}")
        print(f"       {idea.idea}")
        print(f"       Bold because: {idea.bold_because}")
        print(f"       Scores ({len(idea.scores)}):")
        for s in idea.scores:
            print(f"         {s['scorer']}: {s['overall']}/5 — \"{s['reaction']}\"")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P12: 25/10 Crowd Sourcing")
    parser.add_argument("--question", "-q", required=True, help="The challenge to crowd-source ideas for")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles")
    parser.add_argument("--agent-config", help="Path to JSON with custom agents")
    parser.add_argument("--rounds", "-r", type=int, default=5, help="Number of scoring rounds")
    parser.add_argument("--thinking-model", default="claude-opus-4-6")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = TwentyFiveTenOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        scoring_rounds=args.rounds,
    )

    print(f"Running 25/10 with {len(agents)} agents, {args.rounds} scoring rounds")
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)


if __name__ == "__main__":
    main()
