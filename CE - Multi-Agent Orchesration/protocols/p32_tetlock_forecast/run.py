"""CLI entry point for P32: Tetlock Calibrated Forecast Protocol.

Usage:
    python -m protocols.p32_tetlock_forecast.run \
        --question "What is the probability that X happens by 2027?" \
        --agents ceo cfo cto cmo
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import TetlockOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the forecast result."""
    print("\n" + "=" * 70)
    print("TETLOCK CALIBRATED FORECAST")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("STEP 1: FERMI DECOMPOSITION")
    print("-" * 40)
    print(f"\n{result.decomposition}")

    print("\n" + "-" * 40)
    print("STEP 2: BASE RATES")
    print("-" * 40)
    print(f"\n{result.base_rates}")

    print("\n" + "-" * 40)
    print("STEP 3: INSIDE-VIEW ADJUSTMENTS")
    print("-" * 40)
    print(f"\n{result.adjustments}")

    print("\n" + "-" * 40)
    print("STEP 4: FINAL PROBABILITY")
    print("-" * 40)
    print(f"\n{result.final_probability}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P32: Tetlock Calibrated Forecast Protocol")
    parser.add_argument("--question", "-q", required=True, help="The forecasting question")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto cmo)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = TetlockOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Tetlock Calibrated Forecast with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "decomposition": result.decomposition,
            "base_rates": result.base_rates,
            "adjustments": result.adjustments,
            "final_probability": result.final_probability,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
