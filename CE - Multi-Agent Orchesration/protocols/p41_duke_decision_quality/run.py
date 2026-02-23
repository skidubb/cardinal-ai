"""CLI entry point for P41: Duke Decision Quality Separation.

Usage:
    python -m protocols.p41_duke_decision_quality.run \
        --recommendation "We should expand into the European market" \
        --reasoning "Our product has strong PMF in English-speaking markets..."
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import DecisionQualityOrchestrator


DIMENSION_LABELS = {
    "evidence_considered": "Evidence Considered",
    "alternatives_explored": "Alternatives Explored",
    "assumptions_tested": "Assumptions Tested",
    "bias_checks": "Bias Checks",
    "calibration": "Calibration",
}


def print_result(result):
    """Pretty-print the Decision Quality result."""
    print("\n" + "=" * 70)
    print("DUKE DECISION QUALITY EVALUATION")
    print("=" * 70)

    print(f"\nRecommendation: {result.recommendation}\n")

    print("-" * 40)
    print("PROCESS SCORES")
    print("-" * 40)
    for dim, label in DIMENSION_LABELS.items():
        score = result.scores.get(dim, 0)
        justification = result.justifications.get(dim, "N/A")
        bar = "█" * score + "░" * (5 - score)
        print(f"\n  {label}: [{bar}] {score}/5")
        print(f"    {justification}")

    print(f"\n{'=' * 40}")
    print(f"  OVERALL: {result.overall_score:.1f}/5.0")
    print(f"{'=' * 40}")

    print("\n" + "-" * 40)
    print("ASSESSMENT")
    print("-" * 40)
    print(f"\n{result.assessment}")


def main():
    parser = argparse.ArgumentParser(description="P41: Duke Decision Quality Separation")
    parser.add_argument("--recommendation", "-r", required=True, help="The recommendation to evaluate")
    parser.add_argument("--reasoning", required=True, help="The reasoning behind the recommendation")
    parser.add_argument("--question", "-q", help="Original question for context")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for evaluation")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for assessment")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    args = parser.parse_args()

    orchestrator = DecisionQualityOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print("Running Duke Decision Quality evaluation...")
    result = asyncio.run(orchestrator.run(
        recommendation=args.recommendation,
        reasoning=args.reasoning,
        question=args.question,
    ))

    if args.json_output:
        print(json.dumps({
            "recommendation": result.recommendation,
            "reasoning": result.reasoning,
            "scores": result.scores,
            "justifications": result.justifications,
            "overall_score": result.overall_score,
            "assessment": result.assessment,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
