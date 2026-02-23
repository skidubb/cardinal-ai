#!/usr/bin/env python3
"""CLI entry-point for P08: Min Specs protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import textwrap

from .orchestrator import MinSpecsOrchestrator, MinSpecsResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: MinSpecsResult) -> None:
    """Pretty-print the Min Specs result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P08: MIN SPECS RESULT")
    print(sep)
    print(f"\nGoal: {result.question}\n")

    # Phase 2 — All specs (deduplicated)
    print(f"{sep}\nALL CANDIDATE SPECS ({len(result.all_specs)} after dedup)\n{sep}")
    for spec in result.all_specs:
        print(f"  {spec.id}: {spec.description}")

    # Phase 3+4 — Must-haves
    print(f"\n{sep}\nMUST-HAVE SPECS ({len(result.must_haves)})\n{sep}")
    for spec in result.must_haves:
        print(f"  {spec.id}: {spec.description}")

    # Eliminated
    print(f"\n{sep}\nELIMINATED SPECS ({len(result.eliminated)})\n{sep}")
    for spec in result.eliminated:
        print(f"  {spec.id}: {spec.description}")

    # Borderline votes
    if result.borderline_votes:
        print(f"\n{sep}\nBORDERLINE VOTES\n{sep}")
        spec_ids = sorted(set(v.spec_id for v in result.borderline_votes))
        for sid in spec_ids:
            votes = [v for v in result.borderline_votes if v.spec_id == sid]
            keeps = sum(1 for v in votes if v.vote == "KEEP")
            removes = sum(1 for v in votes if v.vote == "REMOVE")
            outcome = "KEPT" if keeps >= removes else "REMOVED"
            print(f"\n  {sid} -> {outcome} ({keeps} keep / {removes} remove)")
            for v in votes:
                print(f"    {v.agent_name}: {v.vote} — {v.rationale}")

    # Final synthesis
    print(f"\n{sep}\nFINAL SYNTHESIS\n{sep}")
    print(result.synthesis)

    # Timings
    print(f"\n{sep}\nTIMINGS\n{sep}")
    total = 0.0
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed:.1f}s")
        total += elapsed
    print(f"  total: {total:.1f}s")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P08: Min Specs — Identify the minimum set of rules for a goal",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The goal or challenge to define minimum specs for.",
    )
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys to use. Available: {', '.join(BUILTIN_AGENTS)}",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=10_000,
        help="Extended thinking budget for Opus calls.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = MinSpecsOrchestrator(
        agents=agents,
        thinking_budget=args.thinking_budget,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "all_specs": [
                {"id": s.id, "description": s.description}
                for s in result.all_specs
            ],
            "must_haves": [
                {"id": s.id, "description": s.description}
                for s in result.must_haves
            ],
            "eliminated": [
                {"id": s.id, "description": s.description}
                for s in result.eliminated
            ],
            "borderline_votes": [
                {"spec_id": v.spec_id, "agent": v.agent_name,
                 "vote": v.vote, "rationale": v.rationale}
                for v in result.borderline_votes
            ],
            "final_min_specs": [
                {"id": s.id, "description": s.description}
                for s in result.final_min_specs
            ],
            "synthesis": result.synthesis,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
