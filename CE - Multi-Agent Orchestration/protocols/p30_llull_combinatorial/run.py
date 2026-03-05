"""CLI entry point for P30: Llull Combinatorial Association Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p30_llull_combinatorial.run \
        --question "How should we price our AI product?" \
        --agents ceo cfo cto

    # With custom agent definitions
    python -m protocols.p30_llull_combinatorial.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import CombinatorialOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Llull Combinatorial result."""
    print("\n" + "=" * 70)
    print("LLULL COMBINATORIAL ASSOCIATION RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("CONCEPT DISKS")
    print("-" * 40)
    for i, disk in enumerate(result.disks):
        name = disk.get("category_name", f"Disk {chr(65 + i)}")
        elements = ", ".join(disk.get("elements", []))
        print(f"  Disk {chr(65 + i)} ({name}): {elements}")

    print("\n" + "-" * 40)
    print("COMBINATIONS (exhaustive)")
    print("-" * 40)
    print(f"\n{result.combinations}")

    print("\n" + "-" * 40)
    print(f"EVALUATIONS ({result.non_obvious_count}/{result.total_count} non-obvious)")
    print("-" * 40)
    print(f"\n{result.evaluations}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P30: Llull Combinatorial Association Protocol")
    parser.add_argument("--question", "-q", required=True, help="The problem or question to explore")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON result")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P30_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P30_DEF.protocol_id}, stages: {[s.name for s in P30_DEF.stages]}")
            return

        client = make_client(protocol_id="p30_llull_combinatorial", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P30_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("LLULL COMBINATORIAL RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = CombinatorialOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Llull Combinatorial with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "disks": result.disks,
            "combinations": result.combinations,
            "evaluations": result.evaluations,
            "non_obvious_count": result.non_obvious_count,
            "total_count": result.total_count,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p30_llull_combinatorial",
            question=args.question,
            agent_keys=[a['name'] for a in agents],
            result=result,
            trace_id=getattr(result, '_langfuse_trace_id', None) or get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
