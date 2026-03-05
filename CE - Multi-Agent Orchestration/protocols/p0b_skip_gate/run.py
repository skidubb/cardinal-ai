#!/usr/bin/env python3
"""CLI entry point for P0b: Cost-Aware Skip Gate."""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

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

    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    args = parser.parse_args()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P0B_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P0B_DEF.protocol_id}, stages: {[s.name for s in P0B_DEF.stages]}")
            return

        client = make_client(protocol_id="p0b_skip_gate", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P0B_DEF, args.question, [], **config))

        print("\n" + "=" * 70)
        print("SKIP GATE RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    gate = SkipGate(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    started_at = datetime.now(timezone.utc)
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
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p0b_skip_gate",
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
