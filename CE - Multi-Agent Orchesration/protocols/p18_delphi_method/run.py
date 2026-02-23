#!/usr/bin/env python3
"""CLI entry point for P18: Delphi Method."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import DelphiOrchestrator, DelphiResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: DelphiResult) -> None:
    """Pretty-print the Delphi result."""
    print("\n" + "=" * 70)
    print("P18: DELPHI METHOD")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Rounds
    for rnd in result.rounds:
        print(f"{'-' * 40}")
        print(f"ROUND {rnd.round_number}")
        print(f"{'-' * 40}")
        for est in rnd.estimates:
            print(f"  {est.agent}: {est.estimate} (range: {est.confidence_low}–{est.confidence_high})")
            print(f"    {est.reasoning[:120]}{'...' if len(est.reasoning) > 120 else ''}")
        print(f"\n  Median: {rnd.median}")
        print(f"  IQR: {rnd.iqr_low} – {rnd.iqr_high} (spread: {rnd.spread})")
        print()

    # Convergence
    print(f"{'-' * 40}")
    print("RESULT")
    print(f"{'-' * 40}")
    status = "CONVERGED" if result.converged else "DID NOT CONVERGE"
    print(f"  Status: {status} after {result.rounds_used} round(s)")
    print(f"  Final estimate (median): {result.final_estimate}")
    print(f"  Confidence interval: {result.confidence_interval[0]} – {result.confidence_interval[1]}")

    # Synthesis
    syn = result.reasoning_summary
    if syn.get("summary"):
        print(f"\n  Summary: {syn['summary']}")
    if syn.get("key_agreements"):
        print("  Key Agreements:")
        for a in syn["key_agreements"]:
            print(f"    - {a}")
    if syn.get("key_disagreements"):
        print("  Key Disagreements:")
        for d in syn["key_disagreements"]:
            print(f"    - {d}")
    if syn.get("evolution_notes"):
        print(f"  Evolution: {syn['evolution_notes']}")

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
        description="P18: Delphi Method — iterative expert estimation with convergence",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The question requiring a numerical estimate.",
    )
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys to use. Available: {', '.join(BUILTIN_AGENTS)}",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum number of estimation rounds (default: 3).",
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

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = DelphiOrchestrator(
        agents=agents,
        max_rounds=args.max_rounds,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "rounds": [
                {
                    "round_number": rnd.round_number,
                    "estimates": [
                        {
                            "agent": est.agent,
                            "estimate": est.estimate,
                            "confidence_low": est.confidence_low,
                            "confidence_high": est.confidence_high,
                            "reasoning": est.reasoning,
                        }
                        for est in rnd.estimates
                    ],
                    "median": rnd.median,
                    "iqr": [rnd.iqr_low, rnd.iqr_high],
                    "spread": rnd.spread,
                }
                for rnd in result.rounds
            ],
            "converged": result.converged,
            "rounds_used": result.rounds_used,
            "final_estimate": result.final_estimate,
            "confidence_interval": list(result.confidence_interval),
            "reasoning_summary": result.reasoning_summary,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
