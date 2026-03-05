"""CLI entry point for P40: Boyd OODA Rapid Cycle Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p40_boyd_ooda.run \
        --question "Competitor just launched a free tier — what do we do?" \
        --agents ceo cfo cto cmo

    # With custom agent definitions
    python -m protocols.p40_boyd_ooda.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import OODAOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the OODA result."""
    print("\n" + "=" * 70)
    print("BOYD OODA RAPID CYCLE RESULTS")
    print("=" * 70)

    print(f"\nSituation: {result.question}")
    print(f"Cycles completed: {len(result.cycles)}\n")

    for cycle in result.cycles:
        print("-" * 40)
        print(f"CYCLE {cycle['cycle_number']}")
        print("-" * 40)

        print("\n  OBSERVE:")
        for line in cycle["observe"].split("\n"):
            print(f"    {line}")

        print("\n  ORIENT:")
        for line in cycle["orient"].split("\n"):
            print(f"    {line}")

        print("\n  DECIDE:")
        for line in cycle["decide"].split("\n"):
            print(f"    {line}")

        print("\n  ACT:")
        for line in cycle["act"].split("\n"):
            print(f"    {line}")

    print("\n" + "=" * 70)
    print("FINAL ACTION")
    print("=" * 70)
    print(f"\n{result.final_action}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P40: Boyd OODA Rapid Cycle Protocol")
    parser.add_argument("--question", "-q", required=True, help="The situation to analyze")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--cycles", "-c", type=int, default=2, help="Number of OODA loops (default: 2)")
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
        from .protocol_def import P40_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P40_DEF.protocol_id}, stages: {[s.name for s in P40_DEF.stages]}")
            return

        client = make_client(protocol_id="p40_boyd_ooda", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P40_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("BOYD OODA RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = OODAOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        num_cycles=args.cycles,
    )

    print(f"Running Boyd OODA Rapid Cycle with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    print(f"Cycles: {args.cycles}")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "cycles": result.cycles,
            "final_action": result.final_action,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p40_boyd_ooda",
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
