#!/usr/bin/env python3
"""CLI entry point for P27: Affinity Mapping."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import AffinityMappingOrchestrator, AffinityMappingResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: AffinityMappingResult) -> None:
    """Pretty-print the Affinity Mapping result."""
    print("\n" + "=" * 70)
    print("P27: AFFINITY MAPPING")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Raw Items
    print("-" * 40)
    print(f"RAW ITEMS ({result.total_items} total)")
    print("-" * 40)
    for agent_name, items in result.raw_items.items():
        print(f"\n  {agent_name} ({len(items)} items):")
        for item in items:
            print(f"    - {item}")

    # Clusters
    print(f"\n{'-' * 40}")
    print(f"CLUSTERS ({len(result.clusters)})")
    print("-" * 40)
    for i, c in enumerate(result.clusters, 1):
        print(f"\n  Cluster {i}: {c.get('theme', 'Unnamed')}")
        for item in c.get("items", []):
            print(f"    - {item}")

    # Themed Clusters
    print(f"\n{'-' * 40}")
    print(f"THEMED CLUSTERS ({len(result.themed_clusters)})")
    print("-" * 40)
    for tc in result.themed_clusters:
        print(f"\n  {tc.get('theme_name', 'Unnamed')}")
        print(f"  Summary: {tc.get('summary', '')}")
        for item in tc.get("items", []):
            print(f"    - {item}")
        misplaced = tc.get("misplaced", [])
        if misplaced:
            print(f"  Misplaced: {misplaced}")

    # Hierarchy
    print(f"\n{'-' * 40}")
    print("THEME HIERARCHY")
    print("-" * 40)
    for mt in result.hierarchy:
        print(f"\n  {mt.get('meta_theme', 'Unnamed')}")
        print(f"  {mt.get('description', '')}")
        for child in mt.get("child_themes", []):
            print(f"    - {child}")

    # Strategic Insights
    print(f"\n{'-' * 40}")
    print("STRATEGIC INSIGHTS")
    print("-" * 40)
    for i, insight in enumerate(result.strategic_insights, 1):
        print(f"  {i}. {insight}")

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
        description="P27: Affinity Mapping — semantic clustering with theme hierarchy",
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
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = AffinityMappingOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "raw_items": result.raw_items,
            "total_items": result.total_items,
            "clusters": result.clusters,
            "themed_clusters": result.themed_clusters,
            "hierarchy": result.hierarchy,
            "strategic_insights": result.strategic_insights,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
