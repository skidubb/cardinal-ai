"""CLI entry point for P12: 25/10 Crowd Sourcing Protocol.

Usage:
    python -m protocols.p12_twenty_five_ten.run \
        --question "Rank these initiatives for a bootstrapped AI consultancy..." \
        --agents ceo cfo cto cmo coo cpo cro
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone

from .orchestrator import TwentyFiveTenOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    print("\n" + "=" * 70)
    print("25/10 CROWD SOURCING RESULTS")
    print("=" * 70)

    print(f"\nChallenge: {result.challenge}")
    print(f"Ideas generated: {len(result.ideas)}")
    print(f"Scoring rounds: {result.scoring_rounds}")
    print(f"Total scores cast: {result.total_scores_cast}\n")

    print("-" * 40)
    print("RANKED IDEAS")
    print("-" * 40)
    for i, idea in enumerate(result.ideas):
        marker = " ★ TOP 25%" if idea.is_top_quartile else ""
        print(f"\n  #{i+1} [{idea.total_score:.0f} pts] {idea.title}{marker}")
        print(f"       Author: {idea.author}")
        print(f"       Avg: Overall={idea.avg_overall:.1f} Bold={idea.avg_boldness:.1f} Feasible={idea.avg_feasibility:.1f} Impact={idea.avg_impact:.1f}")
        print(f"       {idea.idea}")
        print(f"       Bold because: {idea.bold_because}")
        print(f"       Scores ({len(idea.scores)}):")
        for s in idea.scores:
            print(f"         {s['scorer']}: {s['overall']}/5 — \"{s['reaction']}\"")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P12: 25/10 Crowd Sourcing")
    parser.add_argument("--question", "-q", required=True, help="The challenge to crowd-source ideas for")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles")
    parser.add_argument("--agent-config", help="Path to JSON with custom agents")
    parser.add_argument("--rounds", "-r", type=int, default=5, help="Number of scoring rounds")
    parser.add_argument("--thinking-model", default=THINKING_MODEL)
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL)
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)
    orchestrator = TwentyFiveTenOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        scoring_rounds=args.rounds,
    )

    print(f"Running 25/10 with {len(agents)} agents, {args.rounds} scoring rounds")

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P12_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P12_DEF.protocol_id}, stages: {[s.name for s in P12_DEF.stages]}")
            return

        client = make_client(protocol_id="p12_twenty_five_ten", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P12_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("25/10 CROWD SOURCING RESULTS (blackboard)")
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
            protocol_key="p12_twenty_five_ten",
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
