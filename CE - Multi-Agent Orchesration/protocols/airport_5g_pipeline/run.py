#!/usr/bin/env python3
"""CLI entry point for Airport 5G Pipeline — 4-stage chained protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from .orchestrator import Airport5GPipelineOrchestrator, PipelineResult


DEFAULT_AGENT_CONFIG = Path(__file__).resolve().parents[2] / "agents" / "airport_5g_agents.json"

DEFAULT_QUESTION = (
    "How should DFW structure its private 5G deployment to maximize value "
    "for all stakeholders?"
)


def load_agents(config_path: str | Path) -> list[dict]:
    """Load agent definitions from JSON config file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Agent config not found: {path}")
    with open(path) as f:
        return json.load(f)


def print_result(result: PipelineResult) -> None:
    """Pretty-print the full pipeline result."""
    print("\n" + "=" * 70)
    print("AIRPORT 5G PIPELINE — COMPLETE")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")
    print(f"Total elapsed: {result.total_elapsed:.1f}s\n")

    for stage in result.stages:
        print(f"\n{'=' * 70}")
        print(f"STAGE: {stage.stage_name.upper()} ({stage.elapsed_seconds:.1f}s)")
        print("=" * 70)
        # Print first 3000 chars of output with indication if truncated
        output = stage.output
        if len(output) > 3000:
            print(output[:3000])
            print(f"\n... [truncated — {len(output)} chars total]")
        else:
            print(output)

    print(f"\n{'=' * 70}")
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(result.final_recommendation)


def save_result(result: PipelineResult, output_dir: Path) -> None:
    """Save pipeline results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    # Save each stage
    for stage in result.stages:
        stage_file = output_dir / f"{ts}_{stage.stage_name}.md"
        stage_file.write_text(
            f"# Stage: {stage.stage_name.upper()}\n\n"
            f"**Elapsed:** {stage.elapsed_seconds:.1f}s\n\n"
            f"{stage.output}"
        )

    # Save full pipeline result as JSON
    json_file = output_dir / f"{ts}_pipeline_result.json"
    json_data = {
        "question": result.question,
        "total_elapsed": result.total_elapsed,
        "stages": [
            {
                "stage_name": s.stage_name,
                "elapsed_seconds": s.elapsed_seconds,
                "output": s.output,
                "raw_data": s.raw_data,
            }
            for s in result.stages
        ],
        "final_recommendation": result.final_recommendation,
    }
    json_file.write_text(json.dumps(json_data, indent=2, default=str))

    # Save board-ready final report
    report_file = output_dir / f"{ts}_board_report.md"
    report_content = _build_board_report(result)
    report_file.write_text(report_content)

    print(f"\nResults saved to: {output_dir}")
    print(f"  Stage files: {ts}_*.md")
    print(f"  Full data: {ts}_pipeline_result.json")
    print(f"  Board report: {ts}_board_report.md")


def _build_board_report(result: PipelineResult) -> str:
    """Build a comprehensive board-ready report from pipeline results."""
    sections = []

    sections.append("# DFW Airport Private 5G Deployment — Decision-Maker Simulation Report")
    sections.append(f"\n**Strategic Question:** {result.question}")
    sections.append(f"**Analysis Duration:** {result.total_elapsed:.0f} seconds")
    sections.append(f"**Constituencies Modeled:** 6 (Airport CIO, Airport CRO, Anchor Airline VP, Cargo Director, Concessions Tech Lead, AT&T Carrier Rep)")
    sections.append(f"**Protocol Pipeline:** Discover (1-2-4-All) → Diagnose (ACH) → Negotiate (Constraint Negotiation) → Stress-Test (Red/Blue/White)")

    sections.append("\n---\n")

    # Stage 1
    if len(result.stages) > 0:
        sections.append("## Stage 1: Stakeholder Discovery")
        sections.append(f"*Elapsed: {result.stages[0].elapsed_seconds:.0f}s*\n")
        sections.append(result.stages[0].output)

    # Stage 2
    if len(result.stages) > 1:
        sections.append("\n---\n")
        sections.append("## Stage 2: Architecture Diagnosis")
        sections.append(f"*Elapsed: {result.stages[1].elapsed_seconds:.0f}s*\n")
        sections.append(result.stages[1].output)

    # Stage 3
    if len(result.stages) > 2:
        sections.append("\n---\n")
        sections.append("## Stage 3: Constraint Negotiation")
        sections.append(f"*Elapsed: {result.stages[2].elapsed_seconds:.0f}s*\n")
        sections.append(result.stages[2].output)

    # Stage 4
    if len(result.stages) > 3:
        sections.append("\n---\n")
        sections.append("## Stage 4: Stress-Test Results")
        sections.append(f"*Elapsed: {result.stages[3].elapsed_seconds:.0f}s*\n")
        sections.append(result.stages[3].output)

    sections.append("\n---\n")
    sections.append("*Report generated by Cardinal Element's Multi-Agent Decision Simulation Platform*")

    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Airport 5G Pipeline: 4-stage chained protocol simulation",
    )
    parser.add_argument(
        "--question", "-q",
        default=DEFAULT_QUESTION,
        help="The strategic question to analyze.",
    )
    parser.add_argument(
        "--agent-config",
        default=str(DEFAULT_AGENT_CONFIG),
        help="Path to agent config JSON file.",
    )
    parser.add_argument(
        "--thinking-model",
        default="claude-opus-4-6",
        help="Model for agent reasoning (default: claude-opus-4-6).",
    )
    parser.add_argument(
        "--orchestration-model",
        default="claude-haiku-4-5-20251001",
        help="Model for mechanical steps (default: claude-haiku-4-5-20251001).",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=10000,
        help="Token budget for extended thinking (default: 10000).",
    )
    parser.add_argument(
        "--rounds", "-r",
        type=int,
        default=3,
        help="Number of negotiation rounds in Stage 3 (default: 3).",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable JSONL execution tracing.",
    )
    parser.add_argument(
        "--trace-path",
        default=None,
        help="Explicit trace file path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Save results to this directory (creates stage files + board report).",
    )

    args = parser.parse_args()
    agents = load_agents(args.agent_config)

    orchestrator = Airport5GPipelineOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        negotiation_rounds=args.rounds,
        trace=args.trace,
        trace_path=args.trace_path,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "total_elapsed": result.total_elapsed,
            "stages": [
                {
                    "stage_name": s.stage_name,
                    "elapsed_seconds": s.elapsed_seconds,
                    "output": s.output,
                    "raw_data": s.raw_data,
                }
                for s in result.stages
            ],
            "final_recommendation": result.final_recommendation,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print_result(result)

    if args.output_dir:
        save_result(result, Path(args.output_dir))


if __name__ == "__main__":
    main()
