"""CLI entry point for P48: Black Swan Detection & Santa Fe Systems Thinking.

Usage:
    python -m protocols.p48_black_swan_detection.run \
        --question "What black swan risks threaten our AI consulting business?" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from .orchestrator import BlackSwanOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Black Swan Detection result."""
    print("\n" + "=" * 70)
    print("BLACK SWAN DETECTION — ADVERSARIAL ANALYSIS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("LAYER 1: CAUSAL GRAPHS")
    print("-" * 40)
    for i, graph in enumerate(result.causal_graphs, 1):
        print(f"\n  [Agent {i}]")
        print(f"  {graph[:600]}...")

    print("\n" + "-" * 40)
    print("LAYER 2: THRESHOLD SCANS")
    print("-" * 40)
    for i, scan in enumerate(result.threshold_scans, 1):
        print(f"\n  [Agent {i}]")
        print(f"  {scan[:600]}...")

    print("\n" + "-" * 40)
    print(f"LAYER 3: CONFLUENCE SCENARIOS ({len(result.confluences)} found)")
    print("-" * 40)
    for conf in result.confluences:
        name = conf.get("name", conf.get("id", "?"))
        impact = conf.get("estimated_impact", "?")
        prob = conf.get("estimated_probability", "?")
        print(f"  - {name} (impact: {impact}, probability: {prob})")

    print("\n" + "-" * 40)
    print("LAYER 4: HISTORICAL ANALOGUES")
    print("-" * 40)
    for i, analogue in enumerate(result.historical_analogues, 1):
        print(f"\n  [Agent {i}]")
        print(f"  {analogue[:600]}...")

    print("\n" + "=" * 70)
    print("LAYER 5: ADVERSARIAL MEMO")
    print("=" * 70)
    print(f"\n{result.adversarial_memo}")

    print("\n" + "-" * 40)
    print("TIMINGS")
    print("-" * 40)
    for layer, elapsed in result.timings.items():
        print(f"  {layer}: {elapsed:.1f}s")
    total = sum(result.timings.values())
    print(f"  TOTAL: {total:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description="P48: Black Swan Detection & Santa Fe Systems Thinking"
    )
    parser.add_argument(
        "--question", "-q", required=True,
        help="The strategic question or system to analyze for black swan risks",
    )
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)
    orchestrator = BlackSwanOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Black Swan Detection with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
