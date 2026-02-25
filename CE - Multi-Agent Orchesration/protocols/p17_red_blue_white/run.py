#!/usr/bin/env python3
"""CLI entry point for P17: Red/Blue/White Team."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .orchestrator import RedBlueWhiteOrchestrator, RedBlueWhiteResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: RedBlueWhiteResult) -> None:
    """Pretty-print the Red/Blue/White result."""
    print("\n" + "=" * 70)
    print("P17: RED/BLUE/WHITE TEAM")
    print("=" * 70)
    print(f"\nQuestion: {result.question}")
    print(f"\nPlan: {result.plan}\n")

    # Attacks
    print("-" * 40)
    print("RED TEAM ATTACKS")
    print("-" * 40)
    for attack in result.attacks:
        print(f"\n  [{attack.agent}]")
        for v in attack.vulnerabilities:
            vid = v.get("id", "?")
            sev = v.get("severity", "?")
            title = v.get("title", "untitled")
            desc = v.get("description", "")
            print(f"    {vid} ({sev}): {title}")
            print(f"        {desc}")

    # Defenses
    print(f"\n{'-' * 40}")
    print("BLUE TEAM DEFENSES")
    print("-" * 40)
    for defense in result.defenses:
        print(f"\n  [{defense.agent}]")
        for m in defense.mitigations:
            vid = m.get("vulnerability_id", "?")
            dtype = m.get("defense_type", "?")
            response = m.get("response", "")
            print(f"    {vid} ({dtype}): {response[:120]}...")

    # Adjudication
    print(f"\n{'-' * 40}")
    print("WHITE TEAM ADJUDICATION")
    print("-" * 40)
    for adj in result.adjudication:
        icon = {"Resolved": "[OK]", "Partially Resolved": "[~~]", "Open": "[!!]"}.get(adj.verdict, "[??]")
        print(f"  {icon} {adj.vulnerability_id}: {adj.vulnerability_title} ({adj.severity})")
        print(f"      Verdict: {adj.verdict}")
        print(f"      {adj.reasoning[:150]}...")

    # Risk Summary
    print(f"\n{'-' * 40}")
    print("RISK SUMMARY")
    print("-" * 40)
    print(f"\n  Plan Strength Score: {result.plan_strength_score}/10")

    if result.resolved_risks:
        print(f"\n  Resolved Risks ({len(result.resolved_risks)}):")
        for r in result.resolved_risks:
            print(f"    - {r.get('vulnerability_id', '?')}: {r.get('title', '')} — {r.get('summary', '')}")

    if result.open_risks:
        print(f"\n  Open Risks ({len(result.open_risks)}):")
        for r in result.open_risks:
            sev = r.get("severity", "?")
            print(f"    - {r.get('vulnerability_id', '?')} ({sev}): {r.get('title', '')} — {r.get('summary', '')}")

    # Recommendations
    if result.recommendations:
        print(f"\n{'-' * 40}")
        print("RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(result.recommendations, 1):
            print(f"  {i}. {rec}")

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
        description="P17: Red/Blue/White Team — Adversarial Stress-Testing",
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The strategic question being addressed.",
    )
    parser.add_argument(
        "--plan", "-p",
        required=True,
        help="The plan or strategy to stress-test.",
    )
    parser.add_argument(
        "--red", "-r",
        nargs="+",
        default=["cmo", "cfo"],
        help=f"Red team agent keys (attackers). Available: {', '.join(BUILTIN_AGENTS)}",
    )
    parser.add_argument(
        "--blue", "-b",
        nargs="+",
        default=["cto", "coo"],
        help=f"Blue team agent keys (defenders). Available: {', '.join(BUILTIN_AGENTS)}",
    )
    parser.add_argument(
        "--white", "-w",
        default="ceo",
        help=f"White team agent key (arbiter). Available: {', '.join(BUILTIN_AGENTS)}",
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

    args = parser.parse_args()

    red_agents = build_agents(args.red)
    blue_agents = build_agents(args.blue)

    white_key = args.white.lower()
    if white_key not in BUILTIN_AGENTS:
        print(f"Unknown agent: {white_key}. Available: {', '.join(BUILTIN_AGENTS)}")
        sys.exit(1)
    white_agent = BUILTIN_AGENTS[white_key]

    orchestrator = RedBlueWhiteOrchestrator(
        red_agents=red_agents,
        blue_agents=blue_agents,
        white_agent=white_agent,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        trace=args.trace,
        trace_path=args.trace_path,
    )

    result = asyncio.run(orchestrator.run(args.question, args.plan))

    if args.json:
        output = {
            "question": result.question,
            "plan": result.plan,
            "attacks": [
                {"agent": a.agent, "vulnerabilities": a.vulnerabilities}
                for a in result.attacks
            ],
            "defenses": [
                {"agent": d.agent, "mitigations": d.mitigations}
                for d in result.defenses
            ],
            "adjudication": [
                {
                    "vulnerability_id": adj.vulnerability_id,
                    "vulnerability_title": adj.vulnerability_title,
                    "severity": adj.severity,
                    "verdict": adj.verdict,
                    "reasoning": adj.reasoning,
                    "defense_gaps": adj.defense_gaps,
                    "recommended_action": adj.recommended_action,
                }
                for adj in result.adjudication
            ],
            "resolved_risks": result.resolved_risks,
            "open_risks": result.open_risks,
            "plan_strength_score": result.plan_strength_score,
            "recommendations": result.recommendations,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
