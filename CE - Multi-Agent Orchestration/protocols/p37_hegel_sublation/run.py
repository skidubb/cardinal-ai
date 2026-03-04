"""CLI entry point for P37: Hegel Sublation Synthesis.

Usage:
    python -m protocols.p37_hegel_sublation.run \
        --question "Growth vs. profitability in a Series B startup"

    python -m protocols.p37_hegel_sublation.run \
        --question "Should we prioritize speed or quality?" \
        --position-a "Speed: ship fast, iterate, learn from market" \
        --position-b "Quality: build it right, reduce rework, earn trust"
"""

from __future__ import annotations

import argparse
import asyncio
import json


from .orchestrator import SublationOrchestrator
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Sublation result."""
    print("\n" + "=" * 70)
    print("HEGEL SUBLATION SYNTHESIS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("THESIS")
    print("-" * 40)
    print(f"\n{result.thesis}\n")

    print("-" * 40)
    print("ANTITHESIS")
    print("-" * 40)
    print(f"\n{result.antithesis}\n")

    print("=" * 70)
    print("SUBLATION (AUFHEBEN)")
    print("=" * 70)

    if result.preserves:
        print(f"\n--- PRESERVED ---\n{result.preserves}")
    if result.negates:
        print(f"\n--- NEGATED ---\n{result.negates}")
    if result.transcends:
        print(f"\n--- TRANSCENDED ---\n{result.transcends}")

    print("\n" + "=" * 70)
    print("FINAL SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis or result.sublation}")


def print_json(result):
    """Print the result as JSON."""
    print(json.dumps({
        "question": result.question,
        "thesis": result.thesis,
        "antithesis": result.antithesis,
        "sublation": result.sublation,
        "preserves": result.preserves,
        "negates": result.negates,
        "transcends": result.transcends,
        "synthesis": result.synthesis,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="P37: Hegel Sublation Synthesis")
    parser.add_argument("--question", "-q", required=True, help="The tension or conflict to resolve through sublation")
    parser.add_argument("--position-a", help="Explicit thesis position (optional — derived from question if omitted)")
    parser.add_argument("--position-b", help="Explicit antithesis position (optional — derived from question if omitted)")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for all phases")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps (unused in this protocol)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P37_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P37_DEF.protocol_id}, stages: {[s.name for s in P37_DEF.stages]}")
            return

        client = make_client(protocol_id="p37_hegel_sublation", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P37_DEF, args.question, {}, **config))

        print("\n" + "=" * 70)
        print("HEGEL SUBLATION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = SublationOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print("Running Hegel Sublation Synthesis (Thesis -> Antithesis -> Aufheben)")
    result = asyncio.run(orchestrator.run(
        question=args.question,
        position_a=args.position_a,
        position_b=args.position_b,
    ))

    if args.json:
        print_json(result)
    else:
        print_result(result)


if __name__ == "__main__":
    main()
