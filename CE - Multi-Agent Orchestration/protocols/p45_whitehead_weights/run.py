"""CLI entry point for P45: Whitehead Process-Entity Weights.

Usage:
    # Record a performance score
    python -m protocols.p45_whitehead_weights.run record \
        --agent ceo --protocol p16_ach --problem-type diagnostic --score 4.2

    # Recommend agents for a protocol + problem type
    python -m protocols.p45_whitehead_weights.run recommend \
        --protocol p16_ach --problem-type diagnostic
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import WhiteheadOrchestrator


def print_result(result, as_json=False):
    """Pretty-print the weight result."""
    if as_json:
        print(json.dumps({
            "mode": result.mode,
            "recorded_entry": result.recorded_entry,
            "protocol": result.protocol,
            "problem_type": result.problem_type,
            "rankings": result.rankings,
            "synthesis": result.synthesis,
        }, indent=2))
        return

    if result.mode == "record":
        print("\n" + "=" * 50)
        print("WEIGHT RECORDED")
        print("=" * 50)
        e = result.recorded_entry
        print(f"  Agent:        {e['agent']}")
        print(f"  Protocol:     {e['protocol']}")
        print(f"  Problem Type: {e['problem_type']}")
        print(f"  Score:        {e['score']}")
        print(f"  Timestamp:    {e['timestamp']}")

    elif result.mode == "recommend":
        print("\n" + "=" * 50)
        print("AGENT RECOMMENDATIONS")
        print("=" * 50)
        print(f"  Protocol:     {result.protocol}")
        print(f"  Problem Type: {result.problem_type}")

        if not result.rankings:
            print("\n  No performance data found for this combination.")
        else:
            print("\n  " + "-" * 40)
            print("  RANKINGS")
            print("  " + "-" * 40)
            for i, r in enumerate(result.rankings, 1):
                flag = " *" if r["confidence"] == "low" else ""
                print(f"  {i}. {r['agent']}: {r['avg_score']:.2f} (n={r['sample_size']}){flag}")

            low = [r for r in result.rankings if r["confidence"] == "low"]
            if low:
                print(f"\n  * Low confidence (< 10 runs): {', '.join(r['agent'] for r in low)}")

            if result.synthesis:
                print("\n  " + "-" * 40)
                print("  SYNTHESIS")
                print("  " + "-" * 40)
                print(f"\n  {result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P45: Whitehead Process-Entity Weights")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Record subcommand
    rec = subparsers.add_parser("record", help="Record an agent performance score")
    rec.add_argument("--agent", required=True, help="Agent name (e.g., ceo)")
    rec.add_argument("--protocol", required=True, help="Protocol ID (e.g., p16_ach)")
    rec.add_argument("--problem-type", required=True, help="Problem type (e.g., diagnostic)")
    rec.add_argument("--score", type=float, required=True, help="Score (1-5)")

    # Recommend subcommand
    reco = subparsers.add_parser("recommend", help="Recommend agents for a protocol + problem type")
    reco.add_argument("--protocol", required=True, help="Protocol ID (e.g., p16_ach)")
    reco.add_argument("--problem-type", required=True, help="Problem type (e.g., diagnostic)")

    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    orchestrator = WhiteheadOrchestrator()


    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P45_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P45_DEF.protocol_id}, stages: {[s.name for s in P45_DEF.stages]}")
            return

        client = make_client(protocol_id="p45_whitehead_weights", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', 'claude-opus-4-6'),
            "orchestration_model": getattr(args, 'orchestration_model', 'claude-haiku-4-5-20251001'),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P45_DEF, args.command, {}, **config))

        print("\n" + "=" * 70)
        print("WHITEHEAD WEIGHTS RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    if args.command == "record":
        if not 1.0 <= args.score <= 5.0:
            parser.error("Score must be between 1.0 and 5.0")
        result = asyncio.run(orchestrator.record(
            agent_name=args.agent,
            protocol=args.protocol,
            problem_type=args.problem_type,
            score=args.score,
        ))
    elif args.command == "recommend":
        result = asyncio.run(orchestrator.recommend(
            protocol=args.protocol,
            problem_type=args.problem_type,
        ))

    print_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
