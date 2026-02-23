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
import json

from .orchestrator import SixHatsOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents

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
    parser.add_argument("--thinking-model", default="claude-opus-4-6", help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001", help="Model for mechanical steps")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output raw JSON result")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = SixHatsOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    print(f"Running Six Hats with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))

    if args.output_json:
        from dataclasses import asdict
        print(json.dumps(asdict(result), indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
