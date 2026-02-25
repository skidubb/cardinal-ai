"""CLI entry point for P4: Multi-Round Debate Protocol.

Usage:
    python -m protocols.p04_multi_round_debate.run \
        --question "Should we expand into Europe?" \
        --agents ceo cfo cto --rounds 3

    python -m protocols.p04_multi_round_debate.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import DebateOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the debate result."""
    print("\n" + "=" * 70)
    print("MULTI-ROUND DEBATE RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    for rnd in result.rounds:
        print("-" * 40)
        print(f"  Round {rnd.round_number} — {rnd.round_type.upper()}")
        print("-" * 40)
        for arg in rnd.arguments:
            print(f"\n  [{arg.name}]:")
            print(f"  {arg.content}\n")

    print("=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P4: Multi-Round Debate Protocol")
    parser.add_argument("--question", "-q", required=True, help="The question to debate")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--rounds", "-r", type=int, default=3, help="Number of debate rounds (default: 3)")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--trace", action="store_true", help="Enable JSONL execution tracing")
    parser.add_argument("--trace-path", default=None, help="Explicit trace file path")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = DebateOrchestrator(
        agents=agents,
        rounds=args.rounds,
        thinking_model=args.thinking_model,
        thinking_budget=args.thinking_budget,
        trace=args.trace,
        trace_path=args.trace_path,
    )

    print(f"Running {args.rounds}-round debate with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)


if __name__ == "__main__":
    main()
