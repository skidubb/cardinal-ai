#!/usr/bin/env python3
"""CLI for P56: Stigmergic Exploration."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id

from .orchestrator import StigmergicOrchestrator, StigmergicResult


def print_result(result: StigmergicResult) -> None:
    print("\n" + "=" * 70)
    print("P56: STIGMERGIC EXPLORATION — PHEROMONE-BIASED PATH CONVERGENCE")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")

    print("\n" + "-" * 40)
    print("ROUND HISTORY (dominance over time)")
    print("-" * 40)
    for r in result.rounds:
        print(f"  tick {r['tick']}: dominance={r['dominance']:.3f}, paths={len(r['pheromone_map'])}")

    print("\n" + "-" * 40)
    print(f"ALL PATHS ({len(result.paths)})")
    print("-" * 40)
    for p in sorted(result.paths, key=lambda x: -x["pheromone"]):
        print(f"  [{p['path_id']}]  ph={p['pheromone']:.2f}  (seeded by {p['seeded_by']})")
        print(f"         {p['description']}")
        for r in p["refinements"]:
            print(f"         ↳ {r['agent']} (t{r['tick']}): {r['refinement'][:160]}")

    print("\n" + "-" * 40)
    print(f"TOP-{len(result.top_paths)} PATHS (convergence report)")
    print("-" * 40)
    for t in result.top_paths:
        print(f"  #{t['rank']}  [{t['path_id']}]  ph={t['pheromone']:.2f}")
        print(f"      {t['description']}")
        print(f"      seeded by: {t['seeded_by']}, refinements: {len(t['refinements'])}")

    print("\n" + "-" * 40)
    print("TERMINATION")
    print("-" * 40)
    print(f"  reason: {result.termination_reason}")
    print(f"  final dominance: {result.dominance_final:.3f}")

    if result.halts:
        print("\n" + "-" * 40)
        print(f"HALTS ({len(result.halts)})")
        print("-" * 40)
        for h in result.halts:
            print(f"  {h['agent']}: {h['reason']}")

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
        description="P56: Stigmergic Exploration — pheromone-biased path convergence",
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
    parser.add_argument("--ticks", type=int, default=3, help="Max ticks (safety ceiling)")
    parser.add_argument("--seed-k", type=int, default=2, help="Paths per agent in seed round")
    parser.add_argument("--decay", type=float, default=0.85, help="Per-tick pheromone decay rate")
    parser.add_argument("--boost", type=float, default=1.5, help="Reinforce multiplier")
    parser.add_argument("--dominance", type=float, default=0.5, help="Termination threshold on top path share")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    agents = build_agents(args.agents, mode=args.mode)
    orchestrator = StigmergicOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        max_ticks=args.ticks,
        seed_k=args.seed_k,
        decay_rate=args.decay,
        boost=args.boost,
        dominance_threshold=args.dominance,
    )
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(
            json.dumps(
                {
                    "question": result.question,
                    "paths": result.paths,
                    "top_paths": result.top_paths,
                    "rounds": result.rounds,
                    "termination_reason": result.termination_reason,
                    "dominance_final": result.dominance_final,
                    "halts": result.halts,
                    "malformed_actions": result.malformed_actions,
                    "decentralization_manifest": result.decentralization_manifest,
                    "timings": result.timings,
                    "run_id": result.run_id,
                },
                indent=2,
                default=str,
            )
        )
    else:
        print_result(result)

    try:
        from protocols.persistence import persist_run
        asyncio.run(
            persist_run(
                protocol_key="p56_stigmergic_exploration",
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
