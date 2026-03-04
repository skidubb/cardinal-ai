"""CLI entry point for P32: Tetlock Calibrated Forecast Protocol.

Usage:
    python -m protocols.p32_tetlock_forecast.run \
        --question "What is the probability that X happens by 2027?" \
        --agents ceo cfo cto cmo
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import TetlockOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    """Pretty-print the forecast result."""
    print("\n" + "=" * 70)
    print("TETLOCK CALIBRATED FORECAST")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("STEP 1: FERMI DECOMPOSITION")
    print("-" * 40)
    print(f"\n{result.decomposition}")

    print("\n" + "-" * 40)
    print("STEP 2: BASE RATES")
    print("-" * 40)
    print(f"\n{result.base_rates}")

    print("\n" + "-" * 40)
    print("STEP 3: INSIDE-VIEW ADJUSTMENTS")
    print("-" * 40)
    print(f"\n{result.adjustments}")

    print("\n" + "-" * 40)
    print("STEP 4: FINAL PROBABILITY")
    print("-" * 40)
    print(f"\n{result.final_probability}")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P32: Tetlock Calibrated Forecast Protocol")
    parser.add_argument("--question", "-q", required=True, help="The forecasting question")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto cmo)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P32_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P32_DEF.protocol_id}, stages: {[s.name for s in P32_DEF.stages]}")
            return

        client = make_client(protocol_id="p32_tetlock_forecast", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P32_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("TETLOCK FORECAST RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = TetlockOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Tetlock Calibrated Forecast with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        print(json.dumps({
            "question": result.question,
            "decomposition": result.decomposition,
            "base_rates": result.base_rates,
            "adjustments": result.adjustments,
            "final_probability": result.final_probability,
            "synthesis": result.synthesis,
        }, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
