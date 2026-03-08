"""CLI entry point for P52: Drift-and-Return Walk Protocol."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from .orchestrator import DriftReturnWalkOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import get_trace_id
from protocols.p49_walk_base.run import print_result


def main():
    parser = argparse.ArgumentParser(description="P52: Drift-and-Return Walk Protocol")
    parser.add_argument("--question", "-q", required=True)
    parser.add_argument("--agents", "-a", nargs="+")
    parser.add_argument("--agent-config", help="Path to custom agent definitions JSON")
    parser.add_argument("--thinking-model", default=THINKING_MODEL)
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL)
    parser.add_argument("--thinking-budget", type=int, default=10000)
    parser.add_argument("--promote-count", type=int, default=4)
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--trace-path", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=["research", "production"], default="production")
    args = parser.parse_args()

    agent_names = args.agents or ["@walk"]
    agents = build_agents(agent_names, args.agent_config, mode=args.mode)
    print(f"Running Drift-Return Walk with {len(agents)} agents")

    if args.dry_run:
        print("[dry-run] Drift-Return Walk, no LLM calls.")
        return

    orchestrator = DriftReturnWalkOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        promote_count=args.promote_count,
        trace=args.trace,
        trace_path=args.trace_path,
    )
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)

    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p52_drift_return_walk",
            question=args.question,
            agent_keys=[a["name"] for a in agents],
            result=result,
            trace_id=get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass


if __name__ == "__main__":
    main()
