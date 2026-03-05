"""CLI entry point for P38: Klein Pre-Mortem Protocol.

Usage:
    python -m protocols.p38_klein_premortem.run \
        --question "We're launching a new product line targeting SMBs" \
        --agents ceo cfo cto cmo
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import PreMortemOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
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
        from .protocol_def import P38_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P38_DEF.protocol_id}, stages: {[s.name for s in P38_DEF.stages]}")
            return

        client = make_client(protocol_id="p38_klein_premortem", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P38_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("KLEIN PRE-MORTEM RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = PreMortemOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Klein Pre-Mortem with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    print(f"Time horizon: {args.time_horizon}")
    started_at = datetime.now(timezone.utc)
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
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p38_klein_premortem",
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
