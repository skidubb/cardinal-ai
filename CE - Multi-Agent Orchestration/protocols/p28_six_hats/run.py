"""CLI entry point for P28: Parallel Thinking (Six Hats) Protocol.

Usage:
    # With built-in agent roles
    python -m protocols.p28_six_hats.run \
        --question "Should we expand into the European market?" \
        --agents ceo cfo cto cmo

    # With custom agent definitions
    python -m protocols.p28_six_hats.run \
        --question "..." \
        --agent-config agents.json
"""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import json

from .orchestrator import SixHatsOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL

HAT_LABELS = {
    "white": "WHITE HAT (Facts)",
    "red": "RED HAT (Emotions)",
    "black": "BLACK HAT (Caution)",
    "yellow": "YELLOW HAT (Optimism)",
    "green": "GREEN HAT (Creativity)",
}


def print_result(result):
    """Pretty-print the Six Hats result."""
    print("\n" + "=" * 70)
    print("SIX THINKING HATS RESULTS")
    print("=" * 70)

    print(f"\nQuestion: {result.question}\n")

    print("-" * 40)
    print("FRAMING (Blue Hat)")
    print("-" * 40)
    print(f"\n{result.framing}\n")

    for hat_key, hat_label in HAT_LABELS.items():
        outputs = result.hat_outputs.get(hat_key, {})
        if not outputs:
            continue
        print("-" * 40)
        print(hat_label)
        print("-" * 40)
        for agent_name, text in outputs.items():
            print(f"\n  [{agent_name}]")
            for line in text.split("\n"):
                print(f"    {line}")
        print()

    print("=" * 70)
    print("SYNTHESIS (Blue Hat)")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P28: Parallel Thinking (Six Hats) Protocol")
    parser.add_argument("--question", "-q", required=True, help="The question to analyze")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g., ceo cfo cto cmo)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output raw JSON result")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P28_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P28_DEF.protocol_id}, stages: {[s.name for s in P28_DEF.stages]}")
            return

        client = make_client(protocol_id="p28_six_hats", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P28_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("SIX HATS RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = SixHatsOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Six Hats with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.output_json:
        from dataclasses import asdict
        print(json.dumps(asdict(result), indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p28_six_hats",
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
