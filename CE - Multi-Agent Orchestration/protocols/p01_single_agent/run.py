"""CLI entry point for P01: Single Agent.

Usage:
    python -m protocols.p01_single_agent.run -q "What is our ARR?" -a cfo
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.langfuse_tracing import get_trace_id

from .orchestrator import SingleAgentOrchestrator
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    print("\n" + "=" * 70)
    print(f"SINGLE AGENT RESPONSE — {result.agent_name}")
    print("=" * 70)
    if result.was_auto_selected:
        fit = f"{result.fit_score:.2f}" if result.fit_score is not None else "?"
        print(f"  (auto-selected from roster · fit={fit})")
        if result.selection_reason:
            print(f"  reason: {result.selection_reason}")
    print(f"\nQuestion: {result.question}\n")
    print("-" * 40)
    print("RESPONSE")
    print("-" * 40)
    print(result.response)


def main():
    parser = argparse.ArgumentParser(description="P01: Single Agent")
    parser.add_argument("--question", "-q", required=True, help="The question to answer")
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        help="One built-in agent role (e.g., ceo). Omit with --auto to auto-select. Extras are ignored.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-select the best-fit agent from the 56-role roster via a Haiku classifier. Ignored if --agents is set.",
    )
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Fallback model when agent has no 'model' field")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for the auto-select classifier (default: Haiku)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking (default: 10000)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output result as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (ServerAgent)")
    args = parser.parse_args()

    if args.agents:
        agents = build_agents(args.agents, args.agent_config, mode=args.mode)
        if not agents:
            parser.error(f"Could not build any agent from keys: {args.agents}")
    elif args.auto:
        agents = []  # Orchestrator will run the classifier and pick one.
    else:
        parser.error("Pass --agents <key> to use a specific role, or --auto to auto-select.")

    orchestrator = SingleAgentOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    if agents:
        primary = agents[0]
        primary_name = getattr(primary, "name", None) or (primary.get("name") if isinstance(primary, dict) else "unknown")
        print(f"Running P01 Single Agent: {primary_name}")
    else:
        print("Running P01 Single Agent: auto-select from 56-agent roster")

    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json_output:
        print(json.dumps({
            "question": result.question,
            "agent_key": result.agent_key,
            "agent_name": result.agent_name,
            "response": result.response,
            "was_auto_selected": result.was_auto_selected,
            "fit_score": result.fit_score,
            "selection_reason": result.selection_reason,
        }, indent=2))
    else:
        print_result(result)

    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p01_single_agent",
            question=args.question,
            agent_keys=[result.agent_key] if result.agent_key else [],
            result=result,
            trace_id=getattr(result, '_langfuse_trace_id', None) or get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
