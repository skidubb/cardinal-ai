#!/usr/bin/env python3
"""CLI entry point for P16: Analysis of Competing Hypotheses."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import ACHOrchestrator, ACHResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: ACHResult) -> None:
    """Pretty-print the ACH result."""
    print("\n" + "=" * 70)
    print("P16: ANALYSIS OF COMPETING HYPOTHESES")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Hypotheses
    print("-" * 40)
    print("HYPOTHESES")
    print("-" * 40)
    for h in result.hypotheses:
        status = " [ELIMINATED]" if h.eliminated else ""
        print(f"  {h.id}: {h.label}{status}")
        print(f"      {h.description}")
        print(f"      Inconsistencies: {h.inconsistency_count}")

    # Evidence
    print(f"\n{'-' * 40}")
    print("EVIDENCE")
    print("-" * 40)
    for ev in result.evidence:
        diag = f" (diagnosticity: {ev.diagnostic_score:.2f})" if ev.diagnostic_score > 0 else ""
        print(f"  {ev.id}: {ev.description}{diag}")

    # Matrix
    print(f"\n{'-' * 40}")
    print("EVIDENCE-HYPOTHESIS MATRIX (aggregated)")
    print("-" * 40)
    from collections import Counter
    vote_buckets: dict[tuple[str, str], list[str]] = {}
    for cell in result.matrix:
        key = (cell.evidence_id, cell.hypothesis_id)
        vote_buckets.setdefault(key, []).append(cell.score)
    aggregated = {k: Counter(v).most_common(1)[0][0] for k, v in vote_buckets.items()}

    h_ids = [h.id for h in result.hypotheses]
    header = f"{'Evidence':<30} | " + " | ".join(f"{hid:^5}" for hid in h_ids)
    print(header)
    print("-" * len(header))
    for ev in result.evidence:
        scores = [aggregated.get((ev.id, hid), "?") for hid in h_ids]
        row = f"{ev.id:<30} | " + " | ".join(f"{s:^5}" for s in scores)
        print(row)

    # Surviving
    print(f"\n{'-' * 40}")
    print("SURVIVING HYPOTHESES")
    print("-" * 40)
    for h in result.surviving:
        print(f"  {h.id}: {h.label} (inconsistencies: {h.inconsistency_count})")

    # Synthesis
    print(f"\n{'-' * 40}")
    print("SYNTHESIS")
    print("-" * 40)
    syn = result.synthesis
    if syn.get("conclusion"):
        print(f"\n  Conclusion: {syn['conclusion']}")
    if syn.get("confidence"):
        print(f"  Confidence: {syn['confidence']}")
    if syn.get("confidence_reasoning"):
        print(f"  Reasoning: {syn['confidence_reasoning']}")
    if syn.get("key_uncertainties"):
        print("  Key Uncertainties:")
        for u in syn["key_uncertainties"]:
            print(f"    - {u}")
    if syn.get("sensitivity_notes"):
        print(f"  Sensitivity: {syn['sensitivity_notes']}")

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
        description="P16: Analysis of Competing Hypotheses (ACH)",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to analyze.",
    )
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys to use. Available: {', '.join(BUILTIN_AGENTS)}",
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
        "--thinking-budget",
        type=int,
        default=10000,
        help="Token budget for extended thinking (default: 10000).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable JSONL execution tracing.",
    )
    parser.add_argument(
        "--trace-path",
        default=None,
        help="Explicit trace file path.",
    )

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = ACHOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        trace=args.trace,
        trace_path=args.trace_path,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "hypotheses": [
                {"id": h.id, "label": h.label, "description": h.description,
                 "inconsistency_count": h.inconsistency_count, "eliminated": h.eliminated}
                for h in result.hypotheses
            ],
            "evidence": [
                {"id": ev.id, "description": ev.description, "diagnostic_score": ev.diagnostic_score}
                for ev in result.evidence
            ],
            "surviving": [h.id for h in result.surviving],
            "eliminated": [h.id for h in result.eliminated],
            "synthesis": result.synthesis,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
