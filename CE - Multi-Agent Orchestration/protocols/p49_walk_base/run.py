"""CLI entry point for P49: Walk Base Protocol.

Usage:
    python -m protocols.p49_walk_base.run \
        --question "Should we build an AI lab?" \
        --agents @walk
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from .orchestrator import WalkBaseOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import get_trace_id


def print_result(result):
    """Pretty-print the Walk Base result."""
    print("\n" + "=" * 70)
    print("WALK BASE RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    # Frame
    print("-" * 40)
    print("PROBLEM FRAME")
    print("-" * 40)
    print(f"  Objective: {result.frame.objective}")
    for c in result.frame.constraints:
        print(f"  Constraint: {c}")
    for t in result.frame.unresolved_tensions:
        print(f"  Tension: {t}")

    # Shallow outputs
    print(f"\n{'-' * 40}")
    print(f"SHALLOW WALK ({len(result.shallow_outputs)} lenses)")
    print("-" * 40)
    for s in result.shallow_outputs:
        print(f"\n  [{s.lens_family}] {s.agent_name}")
        print(f"    Reframe: {s.reframe}")
        print(f"    Hidden variable: {s.hidden_variable}")

    # Salience
    print(f"\n{'-' * 40}")
    print("SALIENCE RANKINGS")
    print("-" * 40)
    for score in result.salience.ranked_outputs:
        promoted = " [PROMOTED]" if score.agent_key in result.salience.promoted_agents else ""
        print(f"  {score.composite:.1f} — {score.agent_key}{promoted}")
        print(f"    {score.rationale}")

    # Deep outputs
    print(f"\n{'-' * 40}")
    print(f"DEEP WALK ({len(result.deep_outputs)} promoted)")
    print("-" * 40)
    for d in result.deep_outputs:
        print(f"\n  {d.agent_name}")
        print(f"    Thesis: {d.thesis}")
        print(f"    Priority test: {d.priority_test}")

    # Cross-exam
    if result.cross_exam:
        print(f"\n{'-' * 40}")
        print(f"CROSS-EXAMINATION ({len(result.cross_exam)} pairings)")
        print("-" * 40)
        for c in result.cross_exam:
            print(f"\n  {c.challenger_key} → {c.target_key}")
            print(f"    Challenge: {c.strongest_opposing_claim}")
            print(f"    Concession: {c.concession}")

    # Synthesis
    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    if result.synthesis:
        print(f"\nBest interpretation: {result.synthesis.best_current_interpretation}")
        print(f"\nWalk added value: {result.synthesis.walk_added_value}")
        for e in result.synthesis.experiments:
            print(f"  Experiment: {e}")
        for k in result.synthesis.kill_criteria:
            print(f"  Kill criterion: {k}")
    if result.synthesis_text:
        print(f"\n{result.synthesis_text}")


def main():
    parser = argparse.ArgumentParser(description="P49: Walk Base Protocol")
    parser.add_argument("--question", "-q", required=True, help="The question to explore")
    parser.add_argument("--agents", "-a", nargs="+", help="Agent roles or @walk category")
    parser.add_argument("--agent-config", help="Path to custom agent definitions JSON")
    parser.add_argument("--thinking-model", default=THINKING_MODEL)
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL)
    parser.add_argument("--thinking-budget", type=int, default=10000)
    parser.add_argument("--promote-count", type=int, default=4, help="Lenses to promote to deep walk")
    parser.add_argument("--include-wildcard", action="store_true", help="Preserve one orthogonal wildcard")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--trace-path", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit")
    parser.add_argument("--mode", choices=["research", "production"], default="production")
    args = parser.parse_args()

    agent_names = args.agents or ["@walk"]
    agents = build_agents(agent_names, args.agent_config, mode=args.mode)
    print(f"Running Walk Base with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")

    if args.dry_run:
        print("[dry-run] Walk Base, no LLM calls.")
        return

    orchestrator = WalkBaseOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        promote_count=args.promote_count,
        include_wildcard=args.include_wildcard,
        trace=args.trace,
        trace_path=args.trace_path,
    )
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)

    # Persist to Postgres (best-effort)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p49_walk_base",
            question=args.question,
            agent_keys=[a["name"] for a in agents],
            result=result,
            trace_id=get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass


if __name__ == "__main__":
    main()
