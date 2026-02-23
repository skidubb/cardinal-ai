"""CLI entry point for P22: Sequential Pipeline Protocol.

Usage:
    python -m protocols.p22_sequential_pipeline.run --question "..." --agents ceo cfo cto cmo
"""

import argparse
import asyncio
import time

from .orchestrator import SequentialPipelineOrchestrator, SequentialPipelineResult
from protocols.agents import BUILTIN_AGENTS, build_agents


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
    args = parser.parse_args()

    agents = build_agents(args.agents)

    print(f"P22: Sequential Pipeline")
    print(f"Question: {args.question}")
    print(f"Pipeline: {' -> '.join(a['name'] for a in agents)}")
    print()

    orchestrator = SequentialPipelineOrchestrator(
        max_thinking_tokens=args.thinking_tokens,
    )

    start = time.time()
    result = asyncio.run(orchestrator.run(args.question, agents))
    elapsed = time.time() - start

    print_result(result, elapsed)


if __name__ == "__main__":
    main()
