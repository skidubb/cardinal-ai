"""CLI entry point for P29: PMI Enumeration Protocol.

Usage:
    python -m protocols.p29_pmi_enumeration.run \
        --question "We should expand into the European market next quarter"
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import PMIOrchestrator


def print_result(result):
    """Pretty-print the PMI result."""
    print("\n" + "=" * 70)
    print("PMI ENUMERATION RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}")
    print(f"Proposition: {result.proposition}\n")

    print("-" * 40)
    print("PLUS (Positives)")
    print("-" * 40)
    print(result.plus_items)

    print("\n" + "-" * 40)
    print("MINUS (Negatives)")
    print("-" * 40)
    print(result.minus_items)

    print("\n" + "-" * 40)
    print("INTERESTING")
    print("-" * 40)
    print(result.interesting_items)

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P29: PMI Enumeration Protocol")
    parser.add_argument("--question", "-q", required=True, help="The proposition or question to evaluate")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output result as JSON")
    args = parser.parse_args()

    orchestrator = PMIOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print("Running PMI Enumeration (Plus / Minus / Interesting)")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json_output:
        print(json.dumps({
            "question": result.question,
            "proposition": result.proposition,
            "plus_items": result.plus_items,
            "minus_items": result.minus_items,
            "interesting_items": result.interesting_items,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
