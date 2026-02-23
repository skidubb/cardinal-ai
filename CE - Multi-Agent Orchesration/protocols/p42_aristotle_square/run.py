"""CLI entry point for P42: Aristotle Square of Opposition.

Usage:
    python -m protocols.p42_aristotle_square.run \
        --position-a "We should enter the market" \
        --position-b "We should not enter the market"
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import SquareOrchestrator


def print_result(result):
    """Pretty-print the Square of Opposition result."""
    print("\n" + "=" * 70)
    print("ARISTOTLE SQUARE OF OPPOSITION")
    print("=" * 70)

    print(f"\nPosition A: {result.position_a}")
    print(f"Position B: {result.position_b}")

    print(f"\n  Classification:  {result.classification}")
    print(f"  Reasoning:       {result.reasoning}")
    print(f"\n  Recommended:     {result.recommended_protocol}")
    print(f"  Rationale:       {result.routing_rationale}")
    print()


def main():
    parser = argparse.ArgumentParser(description="P42: Aristotle Square of Opposition")
    parser.add_argument("--position-a", "-a", required=True, help="First position")
    parser.add_argument("--position-b", "-b", required=True, help="Second position")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    args = parser.parse_args()

    orchestrator = SquareOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    result = asyncio.run(orchestrator.run(args.position_a, args.position_b))

    if args.json_output:
        print(json.dumps({
            "position_a": result.position_a,
            "position_b": result.position_b,
            "classification": result.classification,
            "reasoning": result.reasoning,
            "recommended_protocol": result.recommended_protocol,
            "routing_rationale": result.routing_rationale,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
