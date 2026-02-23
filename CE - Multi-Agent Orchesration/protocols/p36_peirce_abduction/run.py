"""CLI entry point for P36: Peirce Abduction Cycle.

Usage:
    python -m protocols.p36_peirce_abduction.run \
        --question "Our enterprise churn doubled last quarter despite record NPS" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from .orchestrator import AbductionOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the Abduction Cycle result."""
    print("\n" + "=" * 70)
    print("PEIRCE ABDUCTION CYCLE RESULTS")
    print("=" * 70)

    print(f"\nAnomaly: {result.question}\n")

    for cycle in result.cycles:
        print("-" * 40)
        print(f"CYCLE {cycle['cycle_number']} — Anomaly: {cycle['anomaly'][:80]}")
        print(f"Outcome: {cycle['outcome']}")
        print("-" * 40)

        print("\n  HYPOTHESES:")
        print(f"  {cycle['hypotheses'][:500]}...")

        print("\n  PREDICTIONS:")
        print(f"  {cycle['predictions'][:500]}...")

        print("\n  EVIDENCE ASSESSMENT:")
        print(f"  {cycle['evidence_assessment'][:500]}...")
        print()

    if result.final_hypothesis:
        print("=" * 70)
        print(f"ACCEPTED HYPOTHESIS: {result.final_hypothesis}")
        print("=" * 70)

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P36: Peirce Abduction Cycle")
    parser.add_argument("--question", "-q", required=True, help="The surprising observation or anomaly to explain")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--max-cycles", type=int, default=3, help="Maximum abduction cycles (default: 3)")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = AbductionOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        max_cycles=args.max_cycles,
    )

    print(f"Running Peirce Abduction Cycle with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
