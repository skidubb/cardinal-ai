"""CLI entry point for P44: Kant Architectonic Pre-Router.

Usage:
    python -m protocols.p44_kant_pre_router.run \
        --question "Should we expand into Europe?"
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import KantRouterOrchestrator


def print_result(result):
    """Pretty-print the Kant Pre-Router result."""
    print("\n" + "=" * 70)
    print("KANT ARCHITECTONIC PRE-ROUTER")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("CLASSIFICATION")
    print("-" * 40)
    print(f"  Problem Type: {result.problem_type}")
    print(f"  Modality:     {result.modality}")
    print(f"  Reasoning:    {result.modality_reasoning}")

    print("\n" + "-" * 40)
    print("ROUTING")
    print("-" * 40)
    print(f"  Protocol:  {result.recommended_protocol}")
    print(f"  Rationale: {result.routing_rationale}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="P44: Kant Architectonic Pre-Router")
    parser.add_argument("--question", "-q", required=True, help="The question to classify and route")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for classification")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON result")
    args = parser.parse_args()

    orchestrator = KantRouterOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json_output:
        print(json.dumps({
            "question": result.question,
            "problem_type": result.problem_type,
            "modality": result.modality,
            "modality_reasoning": result.modality_reasoning,
            "recommended_protocol": result.recommended_protocol,
            "routing_rationale": result.routing_rationale,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
