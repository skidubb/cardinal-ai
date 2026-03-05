"""CLI entry point for P46: Incubation Protocol (The Walk).

Usage:
    python -m protocols.p46_incubation.run \
        --question "Should we pivot from B2B to B2C?" \
        --agents ceo cfo cto

    # With prior analysis from a file
    python -m protocols.p46_incubation.run \
        --question "Should we pivot?" \
        --agents ceo cfo cto \
        --prior-analysis @analysis.txt
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import IncubationOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Incubation result."""
    print("\n" + "=" * 70)
    print("INCUBATION PROTOCOL (THE WALK) RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    if result.agent_analyses:
        print("-" * 40)
        print("PHASE 1: AGENT ANALYSES")
        print("-" * 40)
        for agent_name, analysis in result.agent_analyses.items():
            print(f"\n  {agent_name}:")
            for line in analysis.split("\n")[:5]:
                print(f"    {line}")
            if analysis.count("\n") > 5:
                print(f"    ... ({analysis.count(chr(10)) + 1} lines total)")
    elif result.prior_analysis:
        print("-" * 40)
        print("PHASE 1: PRIOR ANALYSIS (provided)")
        print("-" * 40)
        for line in result.prior_analysis.split("\n")[:5]:
            print(f"  {line}")
        if result.prior_analysis.count("\n") > 5:
            print(f"  ... ({result.prior_analysis.count(chr(10)) + 1} lines total)")

    print("\n" + "-" * 40)
    print("PHASE 2: CORE TENSION")
    print("-" * 40)
    print(f"\n  {result.core_tension}")

    print("\n" + "-" * 40)
    print("PHASE 3: FREE ASSOCIATIONS (The Walk)")
    print("-" * 40)
    print(f"\n{result.associations}")

    print("\n" + "=" * 70)
    print("PHASE 4: EVALUATION & SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P46: Incubation Protocol (The Walk)")
    parser.add_argument("--question", "-q", required=True, help="The strategic question to incubate")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--prior-analysis", help="Prior analysis text (prefix with @ to read from file)")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)

    # Handle prior analysis (inline text or @file)
    prior_analysis = ""
    if args.prior_analysis:
        if args.prior_analysis.startswith("@"):
            with open(args.prior_analysis[1:]) as f:
                prior_analysis = f.read()
        else:
            prior_analysis = args.prior_analysis


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P46_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P46_DEF.protocol_id}, stages: {[s.name for s in P46_DEF.stages]}")
            return

        client = make_client(protocol_id="p46_incubation", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P46_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("INCUBATION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = IncubationOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Incubation Protocol with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question, prior_analysis=prior_analysis))

    if args.json:
        import dataclasses
        print(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p46_incubation",
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
