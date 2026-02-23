#!/usr/bin/env python3
"""CLI entry-point for P10: Heard-Seen-Respected protocol."""

from __future__ import annotations

import argparse
import asyncio
import textwrap

from .orchestrator import AgentSpec, HSROrchestrator, HSRResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: HSRResult) -> None:
    """Pretty-print the full HSR result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P10: HEARD-SEEN-RESPECTED RESULT")
    print(sep)
    print(f"\nQuestion: {result.question}\n")

    # Phase 1 — Narratives
    print(f"{sep}\nPHASE 1 — STAKEHOLDER NARRATIVES\n{sep}")
    for name, text in result.narratives.items():
        print(f"\n--- {name} ---")
        print(textwrap.fill(text, width=88))

    # Phase 2 — Reflections
    print(f"\n{sep}\nPHASE 2 — REFLECTIONS\n{sep}")
    for r in result.reflections:
        print(f"\n--- {r['reflector']} reflecting on {r['reflected_on']} ---")
        print(textwrap.fill(r["reflection"], width=88))

    # Phase 3 — Bridge Synthesis
    print(f"\n{sep}\nPHASE 3 — BRIDGE SYNTHESIS\n{sep}")

    print(f"\n--- Common Ground ---")
    print(result.common_ground)

    print(f"\n--- Key Differences ---")
    print(result.key_differences)

    print(f"\n--- Translation Guide ---")
    print(result.translation_guide)

    # Stats
    print(f"\n{sep}\nSTATS\n{sep}")
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed}s")
    for model, count in result.model_calls.items():
        print(f"  {model}: {count} calls")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="P10: Heard-Seen-Respected — Empathy & perspective translation protocol",
    )
    parser.add_argument("--question", "-q", required=True, help="Strategic challenge to explore")
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help="Agent keys to include (default: ceo cfo cto cmo)",
    )
    parser.add_argument("--thinking-budget", type=int, default=10_000, help="Extended thinking budget")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    agent_dicts = build_agents(args.agents)
    agents = [AgentSpec(name=a["name"], system_prompt=a["system_prompt"]) for a in agent_dicts]
    orchestrator = HSROrchestrator(agents=agents, thinking_budget=args.thinking_budget)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        import json
        output = {
            "question": result.question,
            "narratives": result.narratives,
            "reflections": result.reflections,
            "common_ground": result.common_ground,
            "key_differences": result.key_differences,
            "translation_guide": result.translation_guide,
            "timings": result.timings,
            "model_calls": result.model_calls,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
