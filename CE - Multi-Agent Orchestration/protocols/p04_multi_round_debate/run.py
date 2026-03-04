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
from datetime import datetime, timezone

from .orchestrator import DebateOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL
from protocols.langfuse_tracing import get_trace_id


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--trace", action="store_true", help="Enable JSONL execution tracing")
    parser.add_argument("--trace-path", default=None, help="Explicit trace file path")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)
    orchestrator = DebateOrchestrator(
        agents=agents,
        rounds=args.rounds,
        thinking_model=args.thinking_model,
        thinking_budget=args.thinking_budget,
        trace=args.trace,
        trace_path=args.trace_path,
    )

    print(f"Running {args.rounds}-round debate with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P04_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P04_DEF.protocol_id}, stages: {[s.name for s in P04_DEF.stages]}")
            return

        client = make_client(protocol_id="p04_multi_round_debate", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P04_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("MULTI-ROUND DEBATE RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)

    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p04_multi_round_debate",
            question=args.question,
            agent_keys=[a["name"] for a in agents],
            result=result,
            trace_id=get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
