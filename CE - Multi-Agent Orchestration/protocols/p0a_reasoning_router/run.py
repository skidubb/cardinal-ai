#!/usr/bin/env python3
"""CLI entry point for P0a: Reasoning Router."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import ReasoningRouter, RouterResult


def print_result(result: RouterResult) -> None:
    """Pretty-print the routing result."""
    print("\n" + "=" * 70)
    print("P0a: REASONING ROUTER")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Features
    print("-" * 40)
    print("EXTRACTED FEATURES")
    print("-" * 40)
    for key, val in result.features.items():
        print(f"  {key}: {val}")

    # Problem type
    print(f"\n{'-' * 40}")
    print("PROBLEM TYPE CLASSIFICATION")
    print("-" * 40)
    print(f"  Type: {result.problem_type}")
    print(f"  Confidence: {result.problem_type_confidence}%")

    # Recommendation
    print(f"\n{'-' * 40}")
    print("RECOMMENDED PROTOCOL")
    print("-" * 40)
    print(f"  Protocol: {result.recommended_protocol} — {result.recommended_name}")
    print(f"  Cost Tier: {result.cost_tier}")
    print(f"  Reasoning: {result.reasoning}")

    # Alternatives
    if result.alternatives:
        print(f"\n{'-' * 40}")
        print("ALTERNATIVES")
        print("-" * 40)
        for alt in result.alternatives:
            print(f"  {alt.protocol} — {alt.name}")
            print(f"    When: {alt.reason}")

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
        description="P0a: Reasoning Router — classify a question and recommend a protocol",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to route.",
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

    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    args = parser.parse_args()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P0A_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P0A_DEF.protocol_id}, stages: {[s.name for s in P0A_DEF.stages]}")
            return

        client = make_client(protocol_id="p0a_reasoning_router", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P0A_DEF, args.question, [], **config))

        print("\n" + "=" * 70)
        print("REASONING ROUTER RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    router = ReasoningRouter(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(router.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "features": result.features,
            "problem_type": result.problem_type,
            "problem_type_confidence": result.problem_type_confidence,
            "recommended_protocol": result.recommended_protocol,
            "recommended_name": result.recommended_name,
            "alternatives": [
                {"protocol": a.protocol, "name": a.name, "reason": a.reason}
                for a in result.alternatives
            ],
            "reasoning": result.reasoning,
            "cost_tier": result.cost_tier,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
