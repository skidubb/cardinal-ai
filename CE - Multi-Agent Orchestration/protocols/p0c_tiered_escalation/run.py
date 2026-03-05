#!/usr/bin/env python3
"""CLI entry point for P0c: Tiered Escalation."""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import TieredEscalation, EscalationResult


def print_result(result: EscalationResult) -> None:
    """Pretty-print the escalation result."""
    print("\n" + "=" * 70)
    print("P0c: TIERED ESCALATION")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Tier progression
    print("-" * 40)
    print("ESCALATION PATH")
    print("-" * 40)
    for tr in result.tier_results:
        status = "ACCEPTED" if tr.tier == result.final_tier else "ESCALATED"
        print(f"  Tier {tr.tier}: confidence={tr.confidence}% → {status}")
        print(f"    {tr.reasoning}")

    print(f"\n  Final tier: {result.final_tier}")
    if result.flagged_for_human:
        print(f"  ⚠ FLAGGED FOR HUMAN REVIEW: {result.flag_reason}")

    # Final response
    print(f"\n{'-' * 40}")
    print("FINAL RESPONSE")
    print("-" * 40)
    print(result.final_response)

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
        description="P0c: Tiered Escalation — cascading protocols on failure",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to process.",
    )
    parser.add_argument(
        "--agents",
        default=None,
        help='JSON array of agent configs, e.g. \'[{"name":"CEO","system_prompt":"..."}]\'',
    )
    parser.add_argument(
        "--confidence-threshold",
        type=int,
        default=80,
        help="Tier 1 confidence threshold (0-100, default: 80).",
    )
    parser.add_argument(
        "--consensus-threshold",
        type=float,
        default=0.7,
        help="Tier 2 consensus threshold (0.0-1.0, default: 0.7).",
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

    agents = None
    if args.agents:
        agents = json.loads(args.agents)


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P0C_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P0C_DEF.protocol_id}, stages: {[s.name for s in P0C_DEF.stages]}")
            return

        client = make_client(protocol_id="p0c_tiered_escalation", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P0C_DEF, args.question, [], **config))

        print("\n" + "=" * 70)
        print("TIERED ESCALATION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    escalation = TieredEscalation(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        confidence_threshold=args.confidence_threshold,
        consensus_threshold=args.consensus_threshold,
    )

    started_at = datetime.now(timezone.utc)
    result = asyncio.run(escalation.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "final_tier": result.final_tier,
            "tier_results": [
                {
                    "tier": tr.tier,
                    "confidence": tr.confidence,
                    "reasoning": tr.reasoning,
                    "response": tr.response[:500] + "..." if len(tr.response) > 500 else tr.response,
                }
                for tr in result.tier_results
            ],
            "final_response": result.final_response,
            "flagged_for_human": result.flagged_for_human,
            "flag_reason": result.flag_reason,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p0c_tiered_escalation",
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
