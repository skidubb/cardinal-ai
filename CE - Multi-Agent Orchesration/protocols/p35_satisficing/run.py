"""CLI entry point for P35: Simon Satisficing Protocol.

Usage:
    python -m protocols.p35_satisficing.run \
        --question "Should we hire a VP of Sales or promote from within?"

    python -m protocols.p35_satisficing.run \
        --question "..." --max-attempts 3 --json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import SatisficingOrchestrator


def print_result(result):
    """Pretty-print the Satisficing result."""
    print("\n" + "=" * 70)
    print("SIMON SATISFICING RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("GOOD-ENOUGH CRITERIA")
    print("-" * 40)
    print(result.criteria)

    print("\n" + "-" * 40)
    print(f"ATTEMPTS ({result.attempts_count} total)")
    print("-" * 40)
    for i, attempt in enumerate(result.attempts, 1):
        status = "ACCEPTED" if attempt["accepted"] else "REJECTED"
        print(f"\n  Attempt {i} [{status}]: {attempt['option']}")
        print(f"  Evaluations: {attempt['evaluations']}")

    if result.accepted_option:
        print("\n" + "-" * 40)
        print("ACCEPTED OPTION")
        print("-" * 40)
        print(f"\n  {result.accepted_option}")
    else:
        print("\n  ** Satisficing FAILED — no option met all thresholds **")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P35: Simon Satisficing Protocol")
    parser.add_argument("--question", "-q", required=True, help="The question or decision to satisfice")
    parser.add_argument("--max-attempts", type=int, default=5, help="Max options to try before failing (default: 5)")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for reasoning phases")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    orchestrator = SatisficingOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        max_attempts=args.max_attempts,
    )

    print(f"Running Simon Satisficing (max {args.max_attempts} attempts)")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "criteria": result.criteria,
            "attempts": result.attempts,
            "accepted_option": result.accepted_option,
            "attempts_count": result.attempts_count,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
