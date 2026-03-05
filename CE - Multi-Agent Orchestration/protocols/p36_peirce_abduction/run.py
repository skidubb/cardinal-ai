"""CLI entry point for P36: Peirce Abduction Cycle.

Usage:
    python -m protocols.p36_peirce_abduction.run \
        --question "Our enterprise churn doubled last quarter despite record NPS" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json
from dataclasses import asdict

from .orchestrator import AbductionOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Abduction Cycle result."""
    print("\n" + "=" * 70)
    print("PEIRCE ABDUCTION CYCLE RESULTS")
    print("=" * 70)

    print(f"\nAnomaly: {result.question}\n")

    for cycle in result.cycles:
        print("-" * 40)
        print(f"CYCLE {cycle['cycle_number']} — Anomaly: {cycle['anomaly'][:80]}")
        print(f"Outcome: {cycle['outcome']}")
        print("-" * 40)

        print("\n  HYPOTHESES:")
        print(f"  {cycle['hypotheses'][:500]}...")

        print("\n  PREDICTIONS:")
        print(f"  {cycle['predictions'][:500]}...")

        print("\n  EVIDENCE ASSESSMENT:")
        print(f"  {cycle['evidence_assessment'][:500]}...")
        print()

    if result.final_hypothesis:
        print("=" * 70)
        print(f"ACCEPTED HYPOTHESIS: {result.final_hypothesis}")
        print("=" * 70)

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P36: Peirce Abduction Cycle")
    parser.add_argument("--question", "-q", required=True, help="The surprising observation or anomaly to explain")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--max-cycles", type=int, default=3, help="Maximum abduction cycles (default: 3)")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
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
        from .protocol_def import P36_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P36_DEF.protocol_id}, stages: {[s.name for s in P36_DEF.stages]}")
            return

        client = make_client(protocol_id="p36_peirce_abduction", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P36_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("PEIRCE ABDUCTION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = AbductionOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        max_cycles=args.max_cycles,
    )

    print(f"Running Peirce Abduction Cycle with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
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
            protocol_key="p36_peirce_abduction",
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
