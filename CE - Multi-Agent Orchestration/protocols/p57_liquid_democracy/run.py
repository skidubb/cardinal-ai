#!/usr/bin/env python3
"""CLI for P57: Liquid Democracy."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id

from .orchestrator import LiquidDemocracyOrchestrator, LiquidDemocracyResult


def print_result(result: LiquidDemocracyResult) -> None:
    print("\n" + "=" * 70)
    print("P57: LIQUID DEMOCRACY — DELEGATION-WEIGHTED BORDA")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")

    print("\n" + "-" * 40)
    print("BALLOT (after dedup)")
    print("-" * 40)
    for b in result.ballot:
        print(f"  [{b['id']}] {b['label']}")
        print(f"         proposed by: {', '.join(b['proposers'])}")

    print("\n" + "-" * 40)
    print("DIRECT VOTES")
    print("-" * 40)
    for v in result.votes:
        print(f"  {v['agent']}: {' > '.join(v['ranking'])}")

    if result.delegations:
        print("\n" + "-" * 40)
        print("DELEGATIONS")
        print("-" * 40)
        for d in result.delegations:
            print(f"  {d['agent']}  →  {d['to']}  (on '{d['topic']}')")

    print("\n" + "-" * 40)
    print("DELEGATION CHAINS (who carries which votes)")
    print("-" * 40)
    for delegate, voters in result.delegation_chains.items():
        if len(voters) > 1:
            print(f"  {delegate}: carries {voters}")

    print("\n" + "-" * 40)
    print("BORDA SCORES (delegation-weighted)")
    print("-" * 40)
    for opt_id, score in result.borda_scores:
        label = next((b["label"] for b in result.ballot if b["id"] == opt_id), opt_id)
        marker = " << WINNER" if opt_id == result.winner_id else ""
        print(f"  [{opt_id}] {score:5.1f}  {label}{marker}")

    print("\n" + "-" * 40)
    print("WINNER")
    print("-" * 40)
    print(f"  [{result.winner_id}] {result.winner_label}")

    print("\n" + "-" * 40)
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
        description="P57: Liquid Democracy — delegation-weighted Borda voting",
    )
    parser.add_argument("--question", "-q", required=True)
    parser.add_argument(
        "--agents", "-a", nargs="+",
        default=["ceo", "cfo", "cto", "cmo", "coo"],
        help=f"Agent keys. Available: {', '.join(sorted(BUILTIN_AGENTS))}",
    )
    parser.add_argument("--thinking-model", default=None)
    parser.add_argument("--orchestration-model", default=None)
    parser.add_argument(
        "--mode", choices=["research", "production"], default="production",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    agents = build_agents(args.agents, mode=args.mode)
    orchestrator = LiquidDemocracyOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(
            json.dumps(
                {
                    "question": result.question,
                    "ballot": result.ballot,
                    "votes": result.votes,
                    "delegations": result.delegations,
                    "effective_votes": result.effective_votes,
                    "delegation_chains": result.delegation_chains,
                    "borda_scores": result.borda_scores,
                    "winner_id": result.winner_id,
                    "winner_label": result.winner_label,
                    "malformed_actions": result.malformed_actions,
                    "decentralization_manifest": result.decentralization_manifest,
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
                protocol_key="p57_liquid_democracy",
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
