"""CLI entry point for P39: Popper Falsification Gate.

Usage:
    python -m protocols.p39_popper_falsification.run \
        --recommendation "We should expand into the European market" \
        --question "How should we grow internationally?" \
        --agents ceo cfo cto
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import FalsificationOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the Falsification result."""
    print("\n" + "=" * 70)
    print("POPPER FALSIFICATION GATE")
    print("=" * 70)

    print(f"\nRecommendation: {result.recommendation}\n")

    print("-" * 40)
    print("FALSIFICATION CONDITIONS")
    print("-" * 40)
    for i, c in enumerate(result.conditions, 1):
        status = "ACTIVATED" if c.get("activated") else "NOT ACTIVATED"
        print(f"\n  {i}. [{status}] {c['condition']}")
        if c.get("reasoning"):
            print(f"     Reasoning: {c['reasoning']}")

    print("\n" + "=" * 70)
    verdict_label = {
        "SURVIVES": "SURVIVES — Recommendation withstands scrutiny",
        "WEAKENED": "WEAKENED — Proceed with caution",
        "FALSIFIED": "FALSIFIED — Recommendation should be reconsidered",
    }.get(result.verdict, result.verdict)
    print(f"VERDICT: {verdict_label}")
    print("=" * 70)
    if result.verdict_reasoning:
        print(f"\n{result.verdict_reasoning}")
    if result.synthesis:
        print(f"\n--- Synthesis ---\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P39: Popper Falsification Gate")
    parser.add_argument("--recommendation", "-r", required=True, help="The recommendation to test")
    parser.add_argument("--question", "-q", default="", help="Original question for context")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
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
        from .protocol_def import P39_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P39_DEF.protocol_id}, stages: {[s.name for s in P39_DEF.stages]}")
            return

        client = make_client(protocol_id="p39_popper_falsification", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P39_DEF, args.recommendation, agents, **config))

        print("\n" + "=" * 70)
        print("POPPER FALSIFICATION RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = FalsificationOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Popper Falsification Gate with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.recommendation, args.question))

    if args.json:
        print(json.dumps({
            "recommendation": result.recommendation,
            "conditions": result.conditions,
            "verdict": result.verdict,
            "verdict_reasoning": result.verdict_reasoning,
            "synthesis": result.synthesis,
        }, indent=2, default=str))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p39_popper_falsification",
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
