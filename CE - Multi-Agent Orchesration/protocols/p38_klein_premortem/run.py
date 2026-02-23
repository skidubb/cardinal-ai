"""CLI entry point for P38: Klein Pre-Mortem Protocol.

Usage:
    python -m protocols.p38_klein_premortem.run \
        --question "We're launching a new product line targeting SMBs" \
        --agents ceo cfo cto cmo
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import PreMortemOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the Pre-Mortem result."""
    print("\n" + "=" * 70)
    print("KLEIN PRE-MORTEM RESULTS")
    print("=" * 70)

    print(f"\nPlan: {result.question}")
    print(f"Time Horizon: {result.time_horizon}\n")

    print("-" * 40)
    print("FAILURE NARRATIVES")
    print("-" * 40)
    for agent_name, narrative in result.narratives.items():
        print(f"\n  --- {agent_name} ---")
        print(f"  {narrative[:300]}..." if len(narrative) > 300 else f"  {narrative}")

    print("\n" + "-" * 40)
    print("FAILURE MODES")
    print("-" * 40)
    convergent = [m for m in result.failure_modes if m.get("type") == "convergent"]
    unique = [m for m in result.failure_modes if m.get("type") == "unique"]

    if convergent:
        print("\n  CONVERGENT (flagged by multiple agents):")
        for m in convergent:
            sources = ", ".join(m.get("sources", []))
            print(f"    [{m['id']}] {m['title']} — sources: {sources}")
            print(f"        {m['description']}")

    if unique:
        print("\n  UNIQUE (flagged by one agent):")
        for m in unique:
            sources = ", ".join(m.get("sources", []))
            print(f"    [{m['id']}] {m['title']} — source: {sources}")
            print(f"        {m['description']}")

    if result.overlooked_signals:
        print("\n" + "-" * 40)
        print("OVERLOOKED SIGNALS")
        print("-" * 40)
        for signal in result.overlooked_signals:
            print(f"  - {signal}")

    print("\n" + "=" * 70)
    print("MITIGATION MAP")
    print("=" * 70)
    print(f"\n{result.mitigation_map}")


def main():
    parser = argparse.ArgumentParser(description="P38: Klein Pre-Mortem Protocol")
    parser.add_argument("--question", "-q", required=True, help="The plan or recommendation to pre-mortem")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--time-horizon", default="18 months", help="Future time horizon (default: 18 months)")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = PreMortemOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Klein Pre-Mortem with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    print(f"Time horizon: {args.time_horizon}")
    result = asyncio.run(orchestrator.run(args.question, time_horizon=args.time_horizon))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "time_horizon": result.time_horizon,
            "narratives": result.narratives,
            "failure_modes": result.failure_modes,
            "overlooked_signals": result.overlooked_signals,
            "mitigation_map": result.mitigation_map,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
