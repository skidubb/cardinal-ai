#!/usr/bin/env python3
"""CLI entry point for P23: Cynefin Probe-Sense-Respond."""

from __future__ import annotations

import argparse
import asyncio
import json

from .orchestrator import CynefinOrchestrator, CynefinResult
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result: CynefinResult) -> None:
    """Pretty-print the Cynefin result."""
    print("\n" + "=" * 70)
    print("P23: CYNEFIN PROBE-SENSE-RESPOND")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")

    # Domain Classification
    print("-" * 40)
    print("DOMAIN CLASSIFICATION")
    print("-" * 40)
    for v in result.domain_votes:
        print(f"  {v.agent_name}: {v.domain.upper()} (confidence: {v.confidence}%)")
        print(f"      {v.reasoning}")

    print(f"\n  Consensus: {result.consensus_domain.upper()}")
    print(f"  Contested: {'Yes' if result.was_contested else 'No'}")

    # Domain Responses
    print(f"\n{'-' * 40}")
    print(f"DOMAIN RESPONSES ({result.consensus_domain.upper()})")
    print("-" * 40)
    for agent_name, resp in result.domain_responses.items():
        print(f"\n  [{agent_name}]")
        for key, value in resp.items():
            if isinstance(value, list):
                print(f"    {key}:")
                for item in value:
                    if isinstance(item, dict):
                        print(f"      - {item.get('name', item.get('description', str(item)))}")
                    else:
                        print(f"      - {item}")
            elif isinstance(value, str) and len(value) > 80:
                print(f"    {key}: {value[:77]}...")
            else:
                print(f"    {key}: {value}")

    # Action Plan
    print(f"\n{'-' * 40}")
    print("ACTION PLAN")
    print("-" * 40)
    plan = result.action_plan
    if plan.get("domain_summary"):
        print(f"\n  Domain: {plan['domain_summary']}")
    if plan.get("action_plan"):
        print(f"\n  Plan: {plan['action_plan']}")
    if plan.get("priority_actions"):
        print("\n  Priority Actions:")
        for i, a in enumerate(plan["priority_actions"], 1):
            print(f"    {i}. {a}")
    if plan.get("risks"):
        print("\n  Risks:")
        for r in plan["risks"]:
            print(f"    - {r}")
    if plan.get("reclassification_triggers"):
        print("\n  Reclassification Triggers:")
        for t in plan["reclassification_triggers"]:
            print(f"    - {t}")
    if plan.get("confidence_note"):
        print(f"\n  Confidence: {plan['confidence_note']}")

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
        description="P23: Cynefin Probe-Sense-Respond",
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

    args = parser.parse_args()
    agents = build_agents(args.agents)

    orchestrator = CynefinOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        output = {
            "question": result.question,
            "domain_votes": {
                v.agent_name: {
                    "domain": v.domain,
                    "reasoning": v.reasoning,
                    "confidence": v.confidence,
                }
                for v in result.domain_votes
            },
            "consensus_domain": result.consensus_domain,
            "was_contested": result.was_contested,
            "domain_responses": result.domain_responses,
            "action_plan": result.action_plan,
            "timings": result.timings,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
