#!/usr/bin/env python3
"""CLI entry point for P13: Ecocycle Planning."""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import EcocyclePlanningOrchestrator, EcocycleResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: EcocycleResult) -> None:
    """Pretty-print the Ecocycle Planning result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P13: ECOCYCLE PLANNING RESULT")
    print(sep)
    print(f"\nQuestion: {result.question}")
    print(f"Initiatives: {len(result.initiatives)}\n")

    # Phase 1 — Agent Assessments
    print(f"{'-' * 40}")
    print("PHASE 1: AGENT ASSESSMENTS")
    print(f"{'-' * 40}")
    for initiative in result.initiatives:
        print(f"\n  [{initiative}]")
        relevant = [a for a in result.agent_assessments if a.initiative.lower().strip() == initiative.lower().strip()]
        for a in relevant:
            print(f"    {a.agent_name}: {a.stage.upper()} — {a.reasoning}")

    # Phase 2 — Consensus
    print(f"\n{'-' * 40}")
    print("PHASE 2: CONSENSUS STAGES")
    print(f"{'-' * 40}")
    for initiative in result.initiatives:
        stage = result.consensus_stages.get(initiative, "unknown")
        contested_marker = " [CONTESTED]" if initiative in result.contested else ""
        print(f"  {initiative} -> {stage.upper()}{contested_marker}")

    # Phase 3 — Action Plans
    print(f"\n{'-' * 40}")
    print("PHASE 3: ACTION PLANS")
    print(f"{'-' * 40}")
    for initiative in result.initiatives:
        stage = result.consensus_stages.get(initiative, "unknown")
        actions = result.action_plans.get(initiative, [])
        print(f"\n  [{initiative}] ({stage.upper()})")
        for i, action in enumerate(actions, 1):
            print(f"    {i}. {action}")

    # Portfolio Summary
    print(f"\n{'-' * 40}")
    print("PORTFOLIO SUMMARY")
    print(f"{'-' * 40}")
    print(f"  {result.portfolio_summary}")

    # Timings
    print(f"\n{'-' * 40}")
    print("TIMINGS")
    print(f"{'-' * 40}")
    total = 0.0
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed:.1f}s")
        total += elapsed
    print(f"  total: {total:.1f}s")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P13: Ecocycle Planning — Lifecycle stage mapping for initiative portfolios",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="Strategic context or question framing the portfolio assessment.",
    )
    parser.add_argument(
        "--initiatives", "-i",
        nargs="+",
        required=True,
        help="List of initiatives/projects to assess (e.g., -i 'Project Alpha' 'Legacy CRM' 'AI Chatbot').",
    )
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help=f"Agent keys to use. Available: {', '.join(BUILTIN_AGENTS)}",
    )
    parser.add_argument(
        "--thinking-model",
        default=None,
        help="Override the thinking model (default: claude-opus-4-6).",
    )
    parser.add_argument(
        "--orchestration-model",
        default=None,
        help="Override the orchestration model (default: claude-haiku-4-5-20251001).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )

    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    args = parser.parse_args()
    agents = build_agents(args.agents, mode=args.mode)


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P13_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P13_DEF.protocol_id}, stages: {[s.name for s in P13_DEF.stages]}")
            return

        client = make_client(protocol_id="p13_ecocycle_planning", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P13_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("ECOCYCLE PLANNING RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = EcocyclePlanningOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question, args.initiatives))

    if args.json:
        output = {
            "question": result.question,
            "initiatives": result.initiatives,
            "agent_assessments": [
                {"agent": a.agent_name, "initiative": a.initiative,
                 "stage": a.stage, "reasoning": a.reasoning}
                for a in result.agent_assessments
            ],
            "consensus_stages": result.consensus_stages,
            "contested": result.contested,
            "action_plans": result.action_plans,
            "portfolio_summary": result.portfolio_summary,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p13_ecocycle_planning",
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
