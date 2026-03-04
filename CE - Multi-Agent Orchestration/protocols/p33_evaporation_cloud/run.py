"""CLI entry point for P33: Goldratt Evaporation Cloud Protocol.

Usage:
    python -m protocols.p33_evaporation_cloud.run \
        --question "We need speed but also need quality" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import EvaporationCloudOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result, as_json=False):
    """Pretty-print the Evaporation Cloud result."""
    if as_json:
        print(json.dumps({
            "question": result.question,
            "cloud": result.cloud,
            "assumptions": result.assumptions,
            "injection_point": result.injection_point,
            "solution": result.solution,
            "synthesis": result.synthesis,
        }, indent=2))
        return

    print("\n" + "=" * 70)
    print("EVAPORATION CLOUD RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("THE CLOUD")
    print("-" * 40)
    c = result.cloud
    print(f"\n  Objective:      {c.get('objective', 'N/A')}")
    print(f"  Requirement A:  {c.get('requirement_a', 'N/A')}")
    print(f"  Requirement B:  {c.get('requirement_b', 'N/A')}")
    print(f"  Prerequisite A: {c.get('prerequisite_a', 'N/A')}")
    print(f"  Prerequisite B: {c.get('prerequisite_b', 'N/A')}")

    print("\n" + "-" * 40)
    print("HIDDEN ASSUMPTIONS BY ARROW")
    print("-" * 40)
    for arrow, assumptions in result.assumptions.items():
        print(f"\n  {arrow}:")
        for i, a in enumerate(assumptions, 1):
            print(f"    {i}. {a}")

    print("\n" + "-" * 40)
    print("INJECTION POINT")
    print("-" * 40)
    print(f"\n  Weakest assumption: {result.injection_point}")
    print(f"\n  Solution: {result.solution}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P33: Goldratt Evaporation Cloud Protocol")
    parser.add_argument("--question", "-q", required=True, help="The conflict or contradiction to dissolve")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P33_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P33_DEF.protocol_id}, stages: {[s.name for s in P33_DEF.stages]}")
            return

        client = make_client(protocol_id="p33_evaporation_cloud", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P33_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("EVAPORATION CLOUD RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = EvaporationCloudOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Evaporation Cloud with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
