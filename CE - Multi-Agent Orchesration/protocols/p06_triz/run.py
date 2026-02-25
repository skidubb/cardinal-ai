"""CLI entry point for P6: TRIZ Inversion Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p06_triz.run \
        --question "We took the $500K enterprise deal outside our ICP" \
        --agents ceo cfo cto cmo

    # With custom agent definitions
    python -m protocols.p06_triz.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import TRIZOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    """Pretty-print the TRIZ result."""
    print("\n" + "=" * 70)
    print("TRIZ INVERSION RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("FAILURE MODES (ranked by risk score)")
    print("-" * 40)
    for f in result.failure_modes:
        sol = next((s for s in result.solutions if s.failure_id == f.id), None)
        print(f"\n  [{f.composite:2d}] {f.title}")
        print(f"       Category: {f.category} | Severity: {f.severity} | Likelihood: {f.likelihood}")
        print(f"       {f.description}")
        if sol:
            print(f"       → Solution: {sol.title}")
            print(f"         {sol.description}")

    print("\n" + "-" * 40)
    print("AGENT CONTRIBUTIONS")
    print("-" * 40)
    for agent_name, contributions in result.agent_contributions.items():
        print(f"\n  {agent_name}: generated {contributions.count(chr(10)) + 1} lines of analysis")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P6: TRIZ Inversion Protocol")
    parser.add_argument("--question", "-q", required=True, help="The plan or question to stress-test")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--trace", action="store_true", help="Enable JSONL execution tracing")
    parser.add_argument("--trace-path", default=None, help="Explicit trace file path")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    print(f"Running TRIZ Inversion with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from protocols.tracing import make_client, BlackboardTracer
        from .protocol_def import P06_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P06_DEF.protocol_id}, stages: {[s.name for s in P06_DEF.stages]}")
            return

        client = make_client(protocol_id="p06_triz", trace=args.trace, trace_path=__import__('pathlib').Path(args.trace_path) if args.trace_path else None)
        config = {
            "client": client,
            "thinking_model": args.thinking_model,
            "orchestration_model": args.orchestration_model,
            "thinking_budget": args.thinking_budget,
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P06_DEF, args.question, agents, **config))

        # Print results from blackboard
        print("\n" + "=" * 70)
        print("TRIZ INVERSION RESULTS (blackboard)")
        print("=" * 70)
        print(f"\nQuestion: {args.question}\n")
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
    else:
        if args.dry_run:
            print("[dry-run] Legacy orchestrator, no LLM calls.")
            return

        orchestrator = TRIZOrchestrator(
            agents=agents,
            thinking_model=args.thinking_model,
            orchestration_model=args.orchestration_model,
            thinking_budget=args.thinking_budget,
            trace=args.trace,
            trace_path=args.trace_path,
        )
        result = asyncio.run(orchestrator.run(args.question))
        print_result(result)


if __name__ == "__main__":
    main()
