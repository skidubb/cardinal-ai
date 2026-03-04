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
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P42_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P42_DEF.protocol_id}, stages: {[s.name for s in P42_DEF.stages]}")
            return

        client = make_client(protocol_id="p42_aristotle_square", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P42_DEF, args.position_a, {}, **config))

        print("\n" + "=" * 70)
        print("ARISTOTLE SQUARE RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

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
