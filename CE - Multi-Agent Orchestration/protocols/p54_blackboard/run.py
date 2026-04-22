#!/usr/bin/env python3
"""CLI for P54: Blackboard (Pandemonium)."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id

from .orchestrator import BlackboardProtocolOrchestrator, BlackboardResult


def print_result(result: BlackboardResult) -> None:
    print("\n" + "=" * 70)
    print("P54: BLACKBOARD (PANDEMONIUM) — SELF-DISPATCHED PEER CONTRIBUTION")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")

    print("\n" + "-" * 40)
    print(f"CONTRIBUTIONS ({len(result.contributions)})")
    print("-" * 40)
    by_topic: dict[str, list[dict]] = {}
    for c in result.contributions:
        by_topic.setdefault(c["topic"], []).append(c)
    for topic in sorted(by_topic.keys()):
        print(f"\n  [{topic}]")
        for c in by_topic[topic]:
            print(f"    {c['agent']} (relevance={c['relevance']:.2f})")
            print(f"      {c['content'][:250]}{'…' if len(c['content']) > 250 else ''}")

    print("\n" + "-" * 40)
    print(f"HALTS ({len(result.halts)})")
    print("-" * 40)
    for h in result.halts:
        print(f"  {h['agent']}: {h['reason']}")

    print("\n" + "-" * 40)
    print("TERMINATION")
    print("-" * 40)
    print(f"  reason: {result.termination_reason}")
    print(f"  ticks run: {result.ticks_run}")

    print("\n" + "-" * 40)
    print("FINAL REPORT (mechanical assembly)")
    print("-" * 40)
    print(result.final_report)

    print("-" * 40)
    print("DECENTRALIZATION MANIFEST")
    print("-" * 40)
    for dim, status in result.decentralization_manifest.items():
        print(f"  {dim:16s}: {status}")

    if result.malformed_actions:
        print("\n" + "-" * 40)
        print(f"MALFORMED ACTIONS ({len(result.malformed_actions)})")
        print("-" * 40)
        for m in result.malformed_actions:
            print(f"  {m['agent']}: {m['error']}")

    print("\n" + "-" * 40)
    print("TIMINGS")
    print("-" * 40)
    total = 0.0
    for stage, elapsed in result.timings.items():
        print(f"  {stage}: {elapsed:.1f}s")
        total += elapsed
    print(f"  total: {total:.1f}s")
    print(f"\n  run_id: {result.run_id}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P54: Blackboard (Pandemonium) — self-dispatched peer contribution",
    )
    parser.add_argument("--question", "-q", required=True)
    parser.add_argument(
        "--agents", "-a", nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys. Available: {', '.join(sorted(BUILTIN_AGENTS))}",
    )
    parser.add_argument("--thinking-model", default=None)
    parser.add_argument("--orchestration-model", default=None)
    parser.add_argument("--mode", choices=["research", "production"], default="production")
    parser.add_argument("--ticks", type=int, default=4, help="Max ticks (safety ceiling)")
    parser.add_argument("--max-entries", type=int, default=80, help="Max Blackboard entries (safety ceiling)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    agents = build_agents(args.agents, mode=args.mode)
    orchestrator = BlackboardProtocolOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        max_ticks=args.ticks,
        max_entries=args.max_entries,
    )
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(
            json.dumps(
                {
                    "question": result.question,
                    "contributions": result.contributions,
                    "halts": result.halts,
                    "final_report": result.final_report,
                    "ticks_run": result.ticks_run,
                    "termination_reason": result.termination_reason,
                    "malformed_actions": result.malformed_actions,
                    "decentralization_manifest": result.decentralization_manifest,
                    "resources": result.resources,
                    "timings": result.timings,
                    "run_id": result.run_id,
                },
                indent=2,
            )
        )
    else:
        print_result(result)

    try:
        from protocols.persistence import persist_run
        asyncio.run(
            persist_run(
                protocol_key="p54_blackboard",
                question=args.question,
                agent_keys=[a["name"] if isinstance(a, dict) else getattr(a, "name", "unknown") for a in agents],
                result=result,
                trace_id=getattr(result, "_langfuse_trace_id", None) or get_trace_id(),
                source="cli",
                started_at=started_at,
            )
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
