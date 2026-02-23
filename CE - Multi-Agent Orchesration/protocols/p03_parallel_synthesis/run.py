"""CLI entry point for P3: Parallel Synthesis Protocol.

Usage:
    python -m protocols.p03_parallel_synthesis.run \
        --question "Should we expand into Europe?" \
        --agents ceo cfo cto

    python -m protocols.p03_parallel_synthesis.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import SynthesisOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the synthesis result."""
    print("\n" + "=" * 70)
    print("PARALLEL SYNTHESIS RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    for p in result.perspectives:
        print("-" * 40)
        print(f"  {p.name}")
        print("-" * 40)
        print(f"{p.response}\n")

    print("=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P3: Parallel Synthesis Protocol")
    parser.add_argument("--question", "-q", required=True, help="The question to analyze")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = SynthesisOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Parallel Synthesis with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)


if __name__ == "__main__":
    main()
