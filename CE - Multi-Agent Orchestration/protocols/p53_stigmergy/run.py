"""CLI entry point for P53: Stigmergic Coordination.

Usage:
    python -m protocols.p53_stigmergy.run \
        --question "Should we expand into Europe?" \
        --agents ceo cfo cto \
        --waves 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import get_trace_id
from protocols.persistence import persist_run

from .orchestrator import (
    DEFAULT_TOP_N_PER_TYPE,
    DEFAULT_WAVES,
    StigmergyOrchestrator,
    StigmergyResult,
    TRACE_TYPES,
)


def print_result(result: StigmergyResult) -> None:
    print("\n" + "=" * 70)
    print(f"P53 STIGMERGY — {result.waves} waves, {len(result.agents)} agents")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")
    print(f"Total traces deposited: {len(result.all_traces)}")

    for trace_type in TRACE_TYPES:
        summaries = result.by_type.get(trace_type, [])
        if not summaries:
            continue
        print("\n" + "-" * 60)
        print(f"  {trace_type.upper()} — top {len(summaries)} locations by cumulative strength")
        print("-" * 60)
        for i, s in enumerate(summaries, start=1):
            contributors = ", ".join(s.contributors)
            print(
                f"  {i}. {s.location} "
                f"(strength={round(s.cumulative_strength, 2)}, "
                f"n={s.trace_count}, contributors={contributors})"
            )
            for content in s.contents[:3]:
                print(f"       • {content}")


def main() -> None:
    parser = argparse.ArgumentParser(description="P53: Stigmergic Coordination")
    parser.add_argument("--question", "-q", required=True, help="Question to analyze")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles (e.g. ceo cfo cto)")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--waves", "-w", type=int, default=DEFAULT_WAVES, help="Number of trace waves (default: 3)")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N_PER_TYPE, help="Top-N locations per trace type in the report (default: 5)")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Model for agent reasoning")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for mechanical steps (unused — harvest is pure Python)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)
    print(
        f"Running Stigmergy with {len(agents)} agents, {args.waves} waves: "
        + ", ".join(a["name"] for a in agents)
    )

    started_at = datetime.now(timezone.utc)
    orch = StigmergyOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        waves=args.waves,
        top_n_per_type=args.top_n,
    )
    result = asyncio.run(orch.run(args.question))

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print_result(result)

    asyncio.run(
        persist_run(
            protocol_key="p53_stigmergy",
            question=args.question,
            agent_keys=[a.get("key", a["name"]) for a in agents],
            result=result,
            trace_id=get_trace_id(),
            source="cli",
            started_at=started_at,
        )
    )


if __name__ == "__main__":
    main()
