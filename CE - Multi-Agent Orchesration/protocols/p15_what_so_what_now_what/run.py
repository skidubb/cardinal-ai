#!/usr/bin/env python3
"""CLI entry-point for P15: What / So What / Now What protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import textwrap

from .orchestrator import WhatSoWhatNowWhatOrchestrator, WhatSoWhatNowWhatResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: WhatSoWhatNowWhatResult) -> None:
    """Pretty-print the What/So What/Now What result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P15: WHAT / SO WHAT / NOW WHAT")
    print(sep)
    print(f"\nQuestion: {result.question}\n")

    # Phase 1 -- WHAT
    print(f"{sep}\nPHASE 1 — WHAT (Individual Observations)\n{sep}")
    for name, text in result.what_observations.items():
        print(f"\n--- {name} ---")
        print(textwrap.fill(text, width=88))

    # Phase 2 -- Consolidated observations
    print(f"\n{sep}\nPHASE 2 — CONSOLIDATED OBSERVATIONS\n{sep}")
    print(result.consolidated_observations)

    # Phase 3 -- SO WHAT
    print(f"\n{sep}\nPHASE 3 — SO WHAT (Individual Implications)\n{sep}")
    for name, text in result.so_what_implications.items():
        print(f"\n--- {name} ---")
        print(textwrap.fill(text, width=88))

    # Phase 4 -- Consolidated implications
    print(f"\n{sep}\nPHASE 4 — CONSOLIDATED IMPLICATIONS\n{sep}")
    print(result.consolidated_implications)

    # Phase 5 -- NOW WHAT
    print(f"\n{sep}\nPHASE 5 — NOW WHAT (Individual Actions)\n{sep}")
    for name, text in result.now_what_actions.items():
        print(f"\n--- {name} ---")
        print(textwrap.fill(text, width=88))

    # Phase 6 -- Final synthesis
    print(f"\n{sep}\nPHASE 6 — FINAL SYNTHESIS\n{sep}")
    print(result.final_synthesis)

    # Timings
    print(f"\n{sep}\nTIMINGS\n{sep}")
    total = 0.0
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed:.1f}s")
        total += elapsed
    print(f"  total: {total:.1f}s")
    for model, count in result.model_calls.items():
        print(f"  {model}: {count} calls")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P15: What / So What / Now What — Three-frame temporal analysis",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question or situation to analyze.",
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

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = WhatSoWhatNowWhatOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "what_observations": result.what_observations,
            "consolidated_observations": result.consolidated_observations,
            "so_what_implications": result.so_what_implications,
            "consolidated_implications": result.consolidated_implications,
            "now_what_actions": result.now_what_actions,
            "final_synthesis": result.final_synthesis,
            "timings": result.timings,
            "model_calls": result.model_calls,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
