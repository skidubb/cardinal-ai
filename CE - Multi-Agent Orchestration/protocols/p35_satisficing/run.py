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
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import SatisficingOrchestrator
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for reasoning phases")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P35_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P35_DEF.protocol_id}, stages: {[s.name for s in P35_DEF.stages]}")
            return

        client = make_client(protocol_id="p35_satisficing", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P35_DEF, args.question, {}, **config))

        print("\n" + "=" * 70)
        print("SATISFICING RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = SatisficingOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        max_attempts=args.max_attempts,
    )

    print(f"Running Simon Satisficing (max {args.max_attempts} attempts)")
    started_at = datetime.now(timezone.utc)
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
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p35_satisficing",
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
