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
from protocols.agents import build_agents
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


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
    parser.add_argument("--thinking-model", default=THINKING_MODEL)
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL)
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Token budget for extended thinking")
    args = parser.parse_args()

    agents = build_agents(args.agents, args.agent_config, mode=args.mode)
    orchestrator = WickedQuestionsOrchestrator(
        agents=agents,
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
    )

    print(f"Running Wicked Questions with {len(agents)} agents: {', '.join(a['name'] for a in agents)}")

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P07_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P07_DEF.protocol_id}, stages: {[s.name for s in P07_DEF.stages]}")
            return

        client = make_client(protocol_id="p07_wicked_questions", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P07_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("WICKED QUESTIONS RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    result = asyncio.run(orchestrator.run(args.question))
    print_result(result)


if __name__ == "__main__":
    main()
