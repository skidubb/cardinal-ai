"""CLI entry point for P47: Pólya Look-Back Protocol.

Usage:
    python -m protocols.p47_polya_lookback.run \
        --question "Should we expand into Europe?" \
        --analysis "The debate concluded that..." \
        --protocol-used p04_multi_round_debate

    # Load analysis from a file
    python -m protocols.p47_polya_lookback.run \
        --question "Should we expand into Europe?" \
        --analysis @smoke-tests/p04_output.txt \
        --protocol-used p04_multi_round_debate
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import LookBackOrchestrator
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Look-Back result."""
    print("\n" + "=" * 70)
    print("POLYA LOOK-BACK RESULTS")
    print("=" * 70)

    print(f"\nOriginal Question: {result.question}")
    print(f"Protocol Used: {result.protocol_used}\n")

    print("-" * 40)
    print("METHOD ANALYSIS")
    print("-" * 40)
    print(f"\n{result.method_analysis}\n")

    print("-" * 40)
    print("GENERALIZATION")
    print("-" * 40)
    print(f"\n{result.generalization}\n")

    print("=" * 70)
    print("ROUTING RULE")
    print("=" * 70)
    print(f"\n{result.routing_rule}\n")


def _load_analysis(value: str) -> str:
    """Load analysis text, or read from file if prefixed with @."""
    if value.startswith("@"):
        with open(value[1:]) as f:
            return f.read()
    return value


def main():
    parser = argparse.ArgumentParser(description="P47: Polya Look-Back Protocol")
    parser.add_argument("--question", "-q", required=True, help="The original question that was analyzed")
    parser.add_argument("--analysis", "-a", required=True, help="The protocol output to reflect on (text or @filepath)")
    parser.add_argument("--protocol-used", "-p", required=True, help="Name of the protocol that produced the analysis")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for reflection phases")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for meta-synthesis")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output result as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    analysis = _load_analysis(args.analysis)


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P47_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P47_DEF.protocol_id}, stages: {[s.name for s in P47_DEF.stages]}")
            return

        client = make_client(protocol_id="p47_polya_lookback", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P47_DEF, args.question, {}, **config))

        print("\n" + "=" * 70)
        print("POLYA LOOKBACK RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = LookBackOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Polya Look-Back on {args.protocol_used} output...")
    result = asyncio.run(orchestrator.run(args.question, analysis, args.protocol_used))

    if args.json_output:
        print(json.dumps({
            "question": result.question,
            "protocol_used": result.protocol_used,
            "method_analysis": result.method_analysis,
            "generalization": result.generalization,
            "routing_rule": result.routing_rule,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
