"""CLI entry point for P29: PMI Enumeration Protocol.

Usage:
    python -m protocols.p29_pmi_enumeration.run \
        --question "We should expand into the European market next quarter"
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import PMIOrchestrator
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output result as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P29_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P29_DEF.protocol_id}, stages: {[s.name for s in P29_DEF.stages]}")
            return

        client = make_client(protocol_id="p29_pmi_enumeration", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P29_DEF, args.question, {}, **config))

        print("\n" + "=" * 70)
        print("PMI ENUMERATION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = PMIOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print("Running PMI Enumeration (Plus / Minus / Interesting)")
    started_at = datetime.now(timezone.utc)
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
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p29_pmi_enumeration",
            question=args.question,
            agent_keys=[],
            result=result,
            trace_id=getattr(result, '_langfuse_trace_id', None) or get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
