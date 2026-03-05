"""CLI entry point for P48: Black Swan Detection & Santa Fe Systems Thinking.

Usage:
    python -m protocols.p48_black_swan_detection.run \
        --question "What black swan risks threaten our AI consulting business?" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
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
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P48_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P48_DEF.protocol_id}, stages: {[s.name for s in P48_DEF.stages]}")
            return

        client = make_client(protocol_id="p48_black_swan_detection", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P48_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("BLACK SWAN DETECTION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = BlackSwanOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Black Swan Detection with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p48_black_swan_detection",
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
