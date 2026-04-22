#!/usr/bin/env python3
"""CLI for P55: Gossip Consensus."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id

from .orchestrator import GossipOrchestrator, GossipResult


def print_result(result: GossipResult) -> None:
    print("\n" + "=" * 70)
    print("P55: GOSSIP CONSENSUS — RANDOM-PAIR PAIRWISE CONVERGENCE")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")
    if result.units_note:
        print(f"Units: {result.units_note}")

    for r, round_estimates in enumerate(result.rounds):
        print("\n" + "-" * 40)
        if r == 0:
            print(f"ROUND {r} — INITIAL ESTIMATES (variance={result.variance_by_round[r]:.3f})")
        else:
            pairs = result.pair_history[r] if r < len(result.pair_history) else []
            pair_str = ", ".join(f"{a}⇄{b}" for a, b in pairs)
            print(f"ROUND {r} — GOSSIP (variance={result.variance_by_round[r]:.3f})")
            if pair_str:
                print(f"         pairs: {pair_str}")
        print("-" * 40)
        for e in round_estimates:
            print(f"  {e['agent']}: value={e['value']}, conf={e['confidence']:.2f}")
            if e["reasoning"]:
                print(f"      {e['reasoning'][:200]}")

    print("\n" + "-" * 40)
    print("CONSENSUS")
    print("-" * 40)
    print(f"  value (confidence-weighted mean): {result.final_consensus}")
    print(f"  rounds run: {len(result.rounds) - 1}")
    print(f"  convergence: {result.convergence_reason}")
    print(f"  final variance: {result.variance_by_round[-1]:.4f}")

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
        description="P55: Gossip Consensus — random-pair pairwise convergence to numeric estimate",
    )
    parser.add_argument("--question", "-q", required=True)
    parser.add_argument(
        "--agents", "-a", nargs="+",
        default=["ceo", "cfo", "cto", "cmo", "coo"],
        help=f"Agent keys. Available: {', '.join(sorted(BUILTIN_AGENTS))}",
    )
    parser.add_argument("--thinking-model", default=None)
    parser.add_argument("--orchestration-model", default=None)
    parser.add_argument("--mode", choices=["research", "production"], default="production")
    parser.add_argument("--rounds", "-r", type=int, default=5, help="Max gossip rounds")
    parser.add_argument("--epsilon", type=float, default=0.25, help="Variance termination threshold")
    parser.add_argument("--seed", type=int, default=None, help="Random pairing seed (default: non-deterministic)")
    parser.add_argument("--units", default="", help="Scale/units note injected into prompts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    agents = build_agents(args.agents, mode=args.mode)
    orchestrator = GossipOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        max_rounds=args.rounds,
        variance_epsilon=args.epsilon,
        rng_seed=args.seed,
        units_note=args.units,
    )
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(
            json.dumps(
                {
                    "question": result.question,
                    "units_note": result.units_note,
                    "rounds": result.rounds,
                    "pair_history": [
                        [list(p) for p in round_pairs] for round_pairs in result.pair_history
                    ],
                    "variance_by_round": result.variance_by_round,
                    "final_consensus": result.final_consensus,
                    "convergence_reason": result.convergence_reason,
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
                protocol_key="p55_gossip_consensus",
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
