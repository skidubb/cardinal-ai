#!/usr/bin/env python3
"""CLI entry point for P20: Borda Count Voting."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .orchestrator import BordaCountOrchestrator, BordaResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: BordaResult) -> None:
    """Pretty-print the Borda Count result."""
    print("\n" + "=" * 70)
    print("P20: BORDA COUNT VOTING")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Options
    print("-" * 40)
    print("OPTIONS")
    print("-" * 40)
    for opt in result.options:
        print(f"  - {opt}")

    # Borda Scores
    print(f"\n{'-' * 40}")
    print("BORDA SCORES")
    print("-" * 40)
    for i, opt in enumerate(result.final_ranking):
        score = result.borda_scores.get(opt, 0)
        marker = " <-- WINNER" if i == 0 else ""
        print(f"  {i + 1}. {opt} — {score} pts{marker}")

    if result.had_tiebreak:
        print("\n  [Condorcet tiebreak was applied]")

    print(f"\n  Margin of victory: {result.margin} pts")

    # Individual Ballots
    print(f"\n{'-' * 40}")
    print("INDIVIDUAL BALLOTS")
    print("-" * 40)
    for ballot in result.ballots:
        print(f"\n  {ballot.agent}:")
        for entry in sorted(ballot.rankings, key=lambda e: e.get("rank", 999)):
            rank = entry.get("rank", "?")
            option = entry.get("option", "?")
            reasoning = entry.get("reasoning", "")
            print(f"    {rank}. {option}")
            if reasoning:
                print(f"       {reasoning}")

    # Reasoning Clusters
    if result.reasoning_clusters:
        print(f"\n{'-' * 40}")
        print("REASONING CLUSTERS")
        print("-" * 40)
        for opt, reasons in result.reasoning_clusters.items():
            print(f"\n  {opt}:")
            for reason in reasons:
                print(f"    - {reason}")

    # Consensus
    print(f"\n{'-' * 40}")
    print("CONSENSUS")
    print("-" * 40)
    print(f"  Score: {result.consensus_score:.2f} / 1.00")

    # Report
    if result.report:
        print(f"\n{'-' * 40}")
        print("REPORT")
        print("-" * 40)
        print(f"\n{result.report}")

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
        description="P20: Borda Count Voting — ranked-choice voting with Borda scoring",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to decide on.",
    )
    parser.add_argument(
        "--options", "-o",
        nargs="+",
        required=True,
        help="The options to rank (2 or more).",
    )
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo", "coo"],
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
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )

    args = parser.parse_args()

    if len(args.options) < 2:
        print("Error: at least 2 options are required for Borda Count voting.")
        sys.exit(1)

    agents = build_agents(args.agents)

    orchestrator = BordaCountOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(orchestrator.run(args.question, args.options))

    if args.json:
        output = {
            "question": result.question,
            "options": result.options,
            "ballots": [
                {"agent": b.agent, "rankings": b.rankings}
                for b in result.ballots
            ],
            "borda_scores": result.borda_scores,
            "final_ranking": result.final_ranking,
            "winner": result.winner,
            "margin": result.margin,
            "had_tiebreak": result.had_tiebreak,
            "reasoning_clusters": result.reasoning_clusters,
            "consensus_score": result.consensus_score,
            "report": result.report,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
