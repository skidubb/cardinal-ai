#!/usr/bin/env python3
"""CLI entry-point for P15: What / So What / Now What protocol."""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
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
        from .protocol_def import P15_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P15_DEF.protocol_id}, stages: {[s.name for s in P15_DEF.stages]}")
            return

        client = make_client(protocol_id="p15_what_so_what_now_what", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P15_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("WHAT/SO WHAT/NOW WHAT RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = WhatSoWhatNowWhatOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    started_at = datetime.now(timezone.utc)
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
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p15_what_so_what_now_what",
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
