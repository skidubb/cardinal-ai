#!/usr/bin/env python3
"""CLI entry point for P26: Crazy Eights — Rapid Divergent Ideation."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import CrazyEightsOrchestrator, CrazyEightsResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: CrazyEightsResult) -> None:
    """Pretty-print the Crazy Eights result."""
    print("\n" + "=" * 70)
    print("P26: CRAZY EIGHTS — RAPID DIVERGENT IDEATION")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Raw ideas per agent
    print("-" * 40)
    print(f"PHASE 1: RAPID GENERATION ({result.total_ideas} ideas total)")
    print("-" * 40)
    for agent_name, ideas in result.raw_ideas.items():
        print(f"\n  {agent_name} ({len(ideas)} ideas):")
        for i, idea in enumerate(ideas, 1):
            print(f"    {i}. {idea}")

    # Clusters
    print(f"\n{'-' * 40}")
    print(f"PHASE 2: CLUSTERS ({len(result.clusters)} themes)")
    print("-" * 40)
    for cluster in result.clusters:
        theme = cluster.get("theme", "Unnamed")
        ideas = cluster.get("ideas", [])
        print(f"\n  [{theme}] ({len(ideas)} ideas)")
        for idea in ideas:
            print(f"    - {idea}")

    # Vote tally
    print(f"\n{'-' * 40}")
    print("PHASE 3: DOT VOTE RESULTS")
    print("-" * 40)
    sorted_votes = sorted(result.vote_tally.items(), key=lambda x: x[1], reverse=True)
    for idea, count in sorted_votes:
        marker = " ***" if idea in result.top_ideas else ""
        print(f"  [{count} votes] {idea}{marker}")

    # Top ideas
    print(f"\n  Top ideas selected: {len(result.top_ideas)}")

    # Developed concepts
    print(f"\n{'-' * 40}")
    print("PHASE 4: DEVELOPED CONCEPTS")
    print("-" * 40)
    for concept in result.developed_concepts:
        print(f"\n  {concept.get('concept_name', 'Unnamed Concept')}")
        print(f"    Original: {concept.get('original_idea', '')}")
        print(f"    Core idea: {concept.get('core_idea', '')}")
        print(f"    Rationale: {concept.get('rationale', '')}")
        print(f"    Key risk: {concept.get('key_risk', '')}")
        print(f"    Next step: {concept.get('next_step', '')}")

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
        description="P26: Crazy Eights — Rapid Divergent Ideation with Dot Voting",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question or challenge to ideate on.",
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
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = CrazyEightsOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "raw_ideas": result.raw_ideas,
            "total_ideas": result.total_ideas,
            "clusters": result.clusters,
            "vote_tally": result.vote_tally,
            "top_ideas": result.top_ideas,
            "developed_concepts": result.developed_concepts,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
