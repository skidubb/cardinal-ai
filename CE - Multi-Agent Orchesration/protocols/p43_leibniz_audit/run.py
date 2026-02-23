"""CLI entry point for P43: Leibniz Auditable Chain.

Usage:
    python -m protocols.p43_leibniz_audit.run \
        --recommendation "We should expand into Europe next quarter" \
        --reasoning "Our US growth is plateauing at 5% QoQ. Europe TAM is 2x..."
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import AuditChainOrchestrator


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
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for reasoning phases")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for verdict phase")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    args = parser.parse_args()

    orchestrator = AuditChainOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print("Running Leibniz Auditable Chain...")
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


if __name__ == "__main__":
    main()
