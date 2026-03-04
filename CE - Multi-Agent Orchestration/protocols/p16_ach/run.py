#!/usr/bin/env python3
"""CLI entry point for P16: Analysis of Competing Hypotheses."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from .orchestrator import ACHOrchestrator, ACHResult
from protocols.agents import BUILTIN_AGENTS, build_agents
from protocols.langfuse_tracing import get_trace_id


def print_result(result: ACHResult) -> None:
    """Pretty-print the ACH result."""
    print("\n" + "=" * 70)
    print("P16: ANALYSIS OF COMPETING HYPOTHESES")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Hypotheses
    print("-" * 40)
    print("HYPOTHESES")
    print("-" * 40)
    for h in result.hypotheses:
        status = " [ELIMINATED]" if h.eliminated else ""
        print(f"  {h.id}: {h.label}{status}")
        print(f"      {h.description}")
        print(f"      Inconsistencies: {h.inconsistency_count}")

    # Evidence
    print(f"\n{'-' * 40}")
    print("EVIDENCE")
    print("-" * 40)
    for ev in result.evidence:
        diag = f" (diagnosticity: {ev.diagnostic_score:.2f})" if ev.diagnostic_score > 0 else ""
        print(f"  {ev.id}: {ev.description}{diag}")

    # Matrix
    print(f"\n{'-' * 40}")
    print("EVIDENCE-HYPOTHESIS MATRIX (aggregated)")
    print("-" * 40)
    from collections import Counter
    vote_buckets: dict[tuple[str, str], list[str]] = {}
    for cell in result.matrix:
        key = (cell.evidence_id, cell.hypothesis_id)
        vote_buckets.setdefault(key, []).append(cell.score)
    aggregated = {
        k: Counter(v).most_common(1)[0][0]
        for k, v in vote_buckets.items()
        if v
    }

    h_ids = [h.id for h in result.hypotheses]
    header = f"{'Evidence':<30} | " + " | ".join(f"{hid:^5}" for hid in h_ids)
    print(header)
    print("-" * len(header))
    for ev in result.evidence:
        scores = [aggregated.get((ev.id, hid), "?") for hid in h_ids]
        row = f"{ev.id:<30} | " + " | ".join(f"{s:^5}" for s in scores)
        print(row)

    # Surviving
    print(f"\n{'-' * 40}")
    print("SURVIVING HYPOTHESES")
    print("-" * 40)
    for h in result.surviving:
        print(f"  {h.id}: {h.label} (inconsistencies: {h.inconsistency_count})")

    # Synthesis
    print(f"\n{'-' * 40}")
    print("SYNTHESIS")
    print("-" * 40)
    syn = result.synthesis
    if syn.get("conclusion"):
        print(f"\n  Conclusion: {syn['conclusion']}")
    if syn.get("confidence"):
        print(f"  Confidence: {syn['confidence']}")
    if syn.get("confidence_reasoning"):
        print(f"  Reasoning: {syn['confidence_reasoning']}")
    if syn.get("key_uncertainties"):
        print("  Key Uncertainties:")
        for u in syn["key_uncertainties"]:
            print(f"    - {u}")
    if syn.get("sensitivity_notes"):
        print(f"  Sensitivity: {syn['sensitivity_notes']}")

    # Timings
    print(f"\n{'-' * 40}")
    print("TIMINGS")
    print("-" * 40)
    total = 0.0
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed:.1f}s")
        total += elapsed
    print(f"  total: {total:.1f}s")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P16: Analysis of Competing Hypotheses (ACH)",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question to analyze.",
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
        "--thinking-budget",
        type=int,
        default=10000,
        help="Token budget for extended thinking (default: 10000).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text.",
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

    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument(
        "--agent-model",
        default=None,
        help="Override the LLM model for all agents (e.g., 'gemini/gemini-3.1-pro-preview'). "
             "When set, agent calls route through LiteLLM instead of Anthropic SDK.",
    )
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()
    agents = build_agents(args.agents, mode=args.mode)

    # Apply agent-model override if specified
    if args.agent_model:
        for agent in agents:
            agent["model"] = args.agent_model


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P16_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P16_DEF.protocol_id}, stages: {[s.name for s in P16_DEF.stages]}")
            return

        client = make_client(protocol_id="p16_ach", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P16_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("ANALYSIS OF COMPETING HYPOTHESES RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = ACHOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
        trace=args.trace,
        trace_path=args.trace_path,
    )

    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "hypotheses": [
                {"id": h.id, "label": h.label, "description": h.description,
                 "inconsistency_count": h.inconsistency_count, "eliminated": h.eliminated}
                for h in result.hypotheses
            ],
            "evidence": [
                {"id": ev.id, "description": ev.description, "diagnostic_score": ev.diagnostic_score}
                for ev in result.evidence
            ],
            "surviving": [h.id for h in result.surviving],
            "eliminated": [h.id for h in result.eliminated],
            "synthesis": result.synthesis,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)

    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p16_ach",
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
