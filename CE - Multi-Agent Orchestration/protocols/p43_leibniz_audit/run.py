"""CLI entry point for P43: Leibniz Auditable Chain.

Usage:
    python -m protocols.p43_leibniz_audit.run \
        --recommendation "We should expand into Europe next quarter" \
        --reasoning "Our US growth is plateauing at 5% QoQ. Europe TAM is 2x..."
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import AuditChainOrchestrator
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the audit chain result."""
    print("\n" + "=" * 70)
    print("LEIBNIZ AUDITABLE CHAIN RESULTS")
    print("=" * 70)

    print(f"\nRecommendation: {result.recommendation[:120]}...")
    print(f"Reasoning: {result.reasoning[:120]}...")

    print("\n" + "-" * 40)
    print("DECOMPOSED STEPS")
    print("-" * 40)
    for step in result.steps:
        v = "VERIFIABLE" if step.get("verifiable") else "OPAQUE"
        print(f"\n  Step {step.get('step_number', '?')}: [{v}]")
        print(f"    Input:     {step.get('input', 'N/A')}")
        print(f"    Operation: {step.get('operation', 'N/A')}")
        print(f"    Output:    {step.get('output', 'N/A')}")

    if result.audit_findings:
        print("\n" + "-" * 40)
        print("AUDIT FINDINGS")
        print("-" * 40)
        for finding in result.audit_findings:
            sev = finding.get("severity", "unknown").upper()
            print(f"\n  Step {finding.get('step_number', '?')} [{sev}]: {finding.get('finding', 'N/A')}")
    else:
        print("\n  No audit findings — all steps passed.")

    print("\n" + "=" * 70)
    print(f"VERDICT: {result.verdict}")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P43: Leibniz Auditable Chain")
    parser.add_argument("--recommendation", "-r", required=True, help="The recommendation to audit")
    parser.add_argument("--reasoning", required=True, help="The reasoning chain to decompose")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for reasoning phases")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for verdict phase")
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
        from .protocol_def import P43_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P43_DEF.protocol_id}, stages: {[s.name for s in P43_DEF.stages]}")
            return

        client = make_client(protocol_id="p43_leibniz_audit", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P43_DEF, args.recommendation, {}, **config))

        print("\n" + "=" * 70)
        print("LEIBNIZ AUDIT RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = AuditChainOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print("Running Leibniz Auditable Chain...")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.recommendation, args.reasoning))

    if args.json_output:
        print(json.dumps({
            "recommendation": result.recommendation,
            "reasoning": result.reasoning,
            "steps": result.steps,
            "audit_findings": result.audit_findings,
            "verdict": result.verdict,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p43_leibniz_audit",
            question=args.recommendation,
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
