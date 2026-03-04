"""CLI entry point for P22: Sequential Pipeline Protocol.

Usage:
    python -m protocols.p22_sequential_pipeline.run --question "..." --agents ceo cfo cto cmo
"""

import argparse
import asyncio
import time
from datetime import datetime, timezone

from .orchestrator import SequentialPipelineOrchestrator, SequentialPipelineResult
from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id


def print_result(result: SequentialPipelineResult, elapsed: float) -> None:
    """Print the pipeline result to stdout."""
    print("\n" + "=" * 80)
    print("P22: SEQUENTIAL PIPELINE — RESULTS")
    print("=" * 80)

    print(f"\nQuestion: {result.question}")
    print(f"Stages: {len(result.stages)}")
    print(f"Quality Gate: {'PASSED' if result.quality_passed else 'FAILED'}")
    print(f"Time: {elapsed:.1f}s")

    print("\n" + "-" * 80)
    print("PROCESSING LINEAGE")
    print("-" * 80)
    for stage in result.stages:
        print(f"\n--- Stage {stage.stage_number}: {stage.agent_name} ---")
        print(stage.content[:500] + ("..." if len(stage.content) > 500 else ""))

    print("\n" + "-" * 80)
    print("FINAL SYNTHESIZED OUTPUT")
    print("-" * 80)
    print(f"\n{result.final_output}")
    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="P22: Sequential Pipeline — agents process in sequence, each building on prior output."
    )
    parser.add_argument(
        "--question", "-q", required=True, help="The strategic question to analyze."
    )
    parser.add_argument(
        "--agents", "-a", nargs="+", default=["ceo", "cfo", "cto"],
        help="Ordered list of agents (order matters). Default: ceo cfo cto. "
             f"Available: {', '.join(BUILTIN_AGENTS.keys())}",
    )
    parser.add_argument(
        "--thinking-tokens", "-t", type=int, default=10000,
        help="Max thinking tokens per stage (default: 10000).",
    )
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument(
        "--agent-model",
        default=None,
        help="Override the LLM model for all agents (e.g., 'gemini/gemini-3.1-pro-preview'). "
             "When set, agent calls route through LiteLLM instead of Anthropic SDK.",
    )
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    args = parser.parse_args()

    agents = build_agents(args.agents, mode=args.mode)
    if args.agent_model:
        for agent in agents:
            agent["model"] = args.agent_model

    print("P22: Sequential Pipeline")
    print(f"Question: {args.question}")
    print(f"Pipeline: {' -> '.join(a['name'] for a in agents)}")
    print()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P22_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P22_DEF.protocol_id}, stages: {[s.name for s in P22_DEF.stages]}")
            return

        client = make_client(protocol_id="p22_sequential_pipeline", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P22_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("SEQUENTIAL PIPELINE RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = SequentialPipelineOrchestrator(
        max_thinking_tokens=args.thinking_tokens,
    )

    started_at = datetime.now(timezone.utc)
    start = time.time()
    result = asyncio.run(orchestrator.run(args.question, agents))
    elapsed = time.time() - start

    print_result(result, elapsed)

    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p22_sequential_pipeline",
            question=args.question,
            agent_keys=[a["name"] for a in agents],
            result=result,
            trace_id=get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
