#!/usr/bin/env python3
"""CLI entry point for P53: Contract Net Protocol — decentralized task allocation."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols._preflight import print_preflight
from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id

from .orchestrator import ContractNetOrchestrator, ContractNetResult


def print_result(result: ContractNetResult) -> None:
    print("\n" + "=" * 70)
    print("P53: CONTRACT NET PROTOCOL — DECENTRALIZED TASK ALLOCATION")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")

    print("\n" + "-" * 40)
    print("TASK BOARD")
    print("-" * 40)
    for t in result.tasks:
        print(f"  [{t['id']}] {t['title']}")
        if t.get("scope"):
            print(f"         {t['scope']}")

    print("\n" + "-" * 40)
    print("BIDS")
    print("-" * 40)
    for b in sorted(result.bids, key=lambda x: (x["task_id"], -x["fit_score"])):
        print(
            f"  {b['agent']:30s} on [{b['task_id']}]  "
            f"fit={b['fit_score']:.2f}  conf={b['confidence']:.2f}  "
            f"cost={b['cost_estimate']}"
        )
        print(f"      approach: {b['approach']}")

    print("\n" + "-" * 40)
    print("AWARDS (Hungarian assignment)")
    print("-" * 40)
    for tid, agent in result.awards.items():
        title = next((t["title"] for t in result.tasks if t["id"] == tid), tid)
        print(f"  [{tid}] {title}  →  {agent}")

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
        description="P53: Contract Net Protocol — decentralized task allocation via bidding",
    )
    parser.add_argument("--question", "-q", required=True, help="The strategic question.")
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys. Available: {', '.join(sorted(BUILTIN_AGENTS))}",
    )
    parser.add_argument("--thinking-model", default=None)
    parser.add_argument("--orchestration-model", default=None)
    parser.add_argument(
        "--mode", choices=["research", "production"], default="production",
        help="Agent mode (default: production)",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted text")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail-fast on preflight errors (Langfuse/ce_db/Postgres/Alembic). Default: WARN only in dev, strict in prod via ENV=production.",
    )
    args = parser.parse_args()

    print_preflight(strict=args.strict or None)

    agents = build_agents(args.agents, mode=args.mode)
    orchestrator = ContractNetOrchestrator(
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
                    "tasks": result.tasks,
                    "bids": result.bids,
                    "awards": result.awards,
                    "deliverables": result.deliverables,
                    "final_report": result.final_report,
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
                protocol_key="p53_contract_net",
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
