"""CLI entry point for P7: Wicked Questions Protocol.

Usage:
    python -m protocols.p07_wicked_questions.run \
        --question "Cardinal Element is scaling from boutique to mid-market" \
        --agents ceo cfo cto cmo coo cpo
"""

from __future__ import annotations

import argparse
import asyncio

from .orchestrator import WickedQuestionsOrchestrator
from protocols.agents import BUILTIN_AGENTS, build_agents


def print_result(result):
    print("\n" + "=" * 70)
    print("WICKED QUESTIONS RESULTS")
    print("=" * 70)

    print(f"\nTopic: {result.topic}")
    print(f"Tensions generated: {result.all_tensions_count}")
    print(f"Passed wickedness test: {result.wicked_count}")
    print(f"Rejected: {result.rejected_count}\n")

    print("-" * 40)
    print("RANKED WICKED QUESTIONS")
    print("-" * 40)
    for wq in result.wicked_questions:
        print(f"\n  [{wq.composite:2d}] {wq.wicked_question}")
        print(f"       Urgency: {wq.urgency} | Impact: {wq.impact} | Hiddenness: {wq.hiddenness}")
        print(f"       Side A: {wq.side_a}")
        print(f"       Side B: {wq.side_b}")
        print(f"       Implication: {wq.strategic_implication}")

    print("\n" + "-" * 40)
    print("AGENT CONTRIBUTIONS")
    print("-" * 40)
    for agent_name, contributions in result.agent_contributions.items():
        print(f"\n  {agent_name}: generated {contributions.count(chr(10)) + 1} lines of analysis")

    print("\n" + "=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(f"\n{result.synthesis}")


def main():
    parser = argparse.ArgumentParser(description="P7: Wicked Questions Protocol")
    parser.add_argument("--question", "-q", required=True, help="The strategic topic to explore")
    parser.add_argument("--agents", "-a", nargs="+", help="Built-in agent roles")
    parser.add_argument("--agent-config", help="Path to JSON file with custom agent definitions")
    parser.add_argument("--thinking-model", default="claude-opus-4-6")
    parser.add_argument("--orchestration-model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config)
    orchestrator = WickedQuestionsOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    print(f"Running Wicked Questions with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")
    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)


if __name__ == "__main__":
    main()
