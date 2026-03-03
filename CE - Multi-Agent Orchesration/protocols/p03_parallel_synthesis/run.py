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

from .orchestrator import SynthesisOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--trace", action="store_true", help="Enable JSONL execution tracing")
    parser.add_argument("--trace-path", default=None, help="Explicit trace file path")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)
    print(f"Running Parallel Synthesis with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from protocols.tracing import make_client
        from .protocol_def import P03_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P03_DEF.protocol_id}, stages: {[s.name for s in P03_DEF.stages]}")
            return

        client = make_client(protocol_id="p03_parallel_synthesis", trace=args.trace, trace_path=__import__('pathlib').Path(args.trace_path) if args.trace_path else None)
        config = {
            "client": client,
            "thinking_model": args.thinking_model,
            "thinking_budget": args.thinking_budget,
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P03_DEF, args.question, agents, **config))

        # Print results from blackboard
        print("\n" + "=" * 70)
        print("PARALLEL SYNTHESIS RESULTS (blackboard)")
        print("=" * 70)
        print(f"\nQuestion: {args.question}\n")
        for entry in bb.read("perspectives"):
            print("-" * 40)
            print(f"  {entry.author}")
            print("-" * 40)
            print(f"{entry.content}\n")
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print("=" * 70)
            print("SYNTHESIS")
            print("=" * 70)
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
    else:
        if args.dry_run:
            print("[dry-run] Legacy orchestrator, no LLM calls.")
            return

        orchestrator = SynthesisOrchestrator(
            agents=agents,
            thinking_model=args.thinking_model,
            thinking_budget=args.thinking_budget,
            trace=args.trace,
            trace_path=args.trace_path,
        )
        result = asyncio.run(orchestrator.run(args.question))
        print_result(result)


if __name__ == "__main__":
    main()
