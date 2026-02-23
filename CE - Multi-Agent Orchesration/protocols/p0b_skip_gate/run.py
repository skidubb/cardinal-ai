#!/usr/bin/env python3
"""CLI entry point for P0b: Cost-Aware Skip Gate."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .orchestrator import SkipGate, SkipGateResult


def print_result(result: SkipGateResult) -> None:
    """Pretty-print the skip gate result."""
    print("\n" + "=" * 70)
    print("P0b: COST-AWARE SKIP GATE")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Features
    print("-" * 40)
    print("EXTRACTED FEATURES")
    print("-" * 40)
    for key, val in result.features.items():
        print(f"  {key}: {val}")

    # Gate Decision
    print(f"\n{'-' * 40}")
    print("GATE DECISION")
    print("-" * 40)
    print(f"  Decision: {result.decision.upper()}")
    print(f"  Confidence: {result.confidence}%")
    print(f"  Cost Savings: {result.estimated_cost_savings}")
    print(f"  Reasoning: {result.reasoning}")

    if result.decision == "skip" and result.single_agent_response:
        print(f"\n{'-' * 40}")
        print("SINGLE AGENT RESPONSE")
        print("-" * 40)
        print(result.single_agent_response)
    elif result.decision == "escalate":
        print(f"\n{'-' * 40}")
        print("ESCALATION RECOMMENDATION")
        print("-" * 40)
        print(f"  Protocol: {result.recommended_protocol} — {result.recommended_name}")

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
        description="P0b: Cost-Aware Skip Gate — decide single-agent vs. multi-agent",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to evaluate.",
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

    gate = SkipGate(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(gate.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "features": result.features,
            "decision": result.decision,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "estimated_cost_savings": result.estimated_cost_savings,
            "single_agent_response": result.single_agent_response,
            "recommended_protocol": result.recommended_protocol,
            "recommended_name": result.recommended_name,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
