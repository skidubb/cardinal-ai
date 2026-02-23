#!/usr/bin/env python3
"""CLI entry point for P25: System Archetype Detection."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .orchestrator import ArchetypeDetector, ArchetypeResult


DEFAULT_AGENTS = [
    {"name": "CEO", "system_prompt": "You are a CEO focused on strategy, vision, and competitive positioning."},
    {"name": "CFO", "system_prompt": "You are a CFO focused on financial analysis, risk, and capital allocation."},
    {"name": "CTO", "system_prompt": "You are a CTO focused on technology strategy, architecture, and innovation."},
    {"name": "COO", "system_prompt": "You are a COO focused on operations, processes, and execution efficiency."},
]


def print_result(result: ArchetypeResult) -> None:
    """Pretty-print the archetype detection result."""
    print("\n" + "=" * 70)
    print("P25: SYSTEM ARCHETYPE DETECTION")
    print("=" * 70)
    print(f"\nSituation: {result.question}\n")

    # Observed dynamics
    print("-" * 40)
    print("OBSERVED DYNAMICS")
    print("-" * 40)
    for d in result.observed_dynamics:
        print(f"  {d.id}: {d.pattern}")
        print(f"    {d.description}")

    # Archetype scores
    print(f"\n{'-' * 40}")
    print("ARCHETYPE SCORES")
    print("-" * 40)
    for name, score in sorted(
        result.archetype_scores.items(), key=lambda x: x[1], reverse=True,
    ):
        bar = "#" * int(score / 5)
        print(f"  {name:30s} {score:5.1f}/100  {bar}")

    # Best matches
    if result.best_matches:
        print(f"\n{'-' * 40}")
        print("BEST-FIT ARCHETYPES")
        print("-" * 40)
        for m in result.best_matches:
            print(f"\n  {m.archetype} (score: {m.score})")
            print(f"  {m.reasoning}")
            if m.structural_mapping:
                print("  Structural mapping:")
                for component, element in m.structural_mapping.items():
                    print(f"    {component} → {element}")

    # Interventions
    if result.interventions:
        print(f"\n{'-' * 40}")
        print("RECOMMENDED INTERVENTIONS")
        print("-" * 40)
        for i, intv in enumerate(result.interventions, 1):
            print(f"\n  {i}. [{intv.get('archetype', '')}] {intv.get('intervention', '')}")
            print(f"     Leverage point: {intv.get('leverage_point', '')}")
            print(f"     Rationale: {intv.get('rationale', '')}")

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
        description="P25: System Archetype Detection — match dynamics to known archetypes",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The situation or system to analyze.",
    )
    parser.add_argument(
        "--agents",
        default=None,
        help='JSON array of agent configs, e.g. \'[{"name":"CEO","system_prompt":"..."}]\'',
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

    agents = DEFAULT_AGENTS
    if args.agents:
        agents = json.loads(args.agents)

    detector = ArchetypeDetector(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(detector.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "observed_dynamics": [
                {"id": d.id, "pattern": d.pattern, "description": d.description}
                for d in result.observed_dynamics
            ],
            "archetype_scores": result.archetype_scores,
            "best_matches": [
                {
                    "archetype": m.archetype,
                    "score": m.score,
                    "structural_mapping": m.structural_mapping,
                    "reasoning": m.reasoning,
                }
                for m in result.best_matches
            ],
            "interventions": result.interventions,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
