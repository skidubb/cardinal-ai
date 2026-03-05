#!/usr/bin/env python3
"""CLI entry-point for P10: Heard-Seen-Respected protocol."""

from __future__ import annotations

import argparse
import asyncio
from protocols.langfuse_tracing import get_trace_id
from datetime import datetime, timezone
import textwrap

from .orchestrator import AgentSpec, HSROrchestrator, HSRResult
from protocols.agents import build_agents


def print_result(result: HSRResult) -> None:
    """Pretty-print the full HSR result."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("P10: HEARD-SEEN-RESPECTED RESULT")
    print(sep)
    print(f"\nQuestion: {result.question}\n")

    # Phase 1 — Narratives
    print(f"{sep}\nPHASE 1 — STAKEHOLDER NARRATIVES\n{sep}")
    for name, text in result.narratives.items():
        print(f"\n--- {name} ---")
        print(textwrap.fill(text, width=88))

    # Phase 2 — Reflections
    print(f"\n{sep}\nPHASE 2 — REFLECTIONS\n{sep}")
    for r in result.reflections:
        print(f"\n--- {r['reflector']} reflecting on {r['reflected_on']} ---")
        print(textwrap.fill(r["reflection"], width=88))

    # Phase 3 — Bridge Synthesis
    print(f"\n{sep}\nPHASE 3 — BRIDGE SYNTHESIS\n{sep}")

    print("\n--- Common Ground ---")
    print(result.common_ground)

    print("\n--- Key Differences ---")
    print(result.key_differences)

    print("\n--- Translation Guide ---")
    print(result.translation_guide)

    # Stats
    print(f"\n{sep}\nSTATS\n{sep}")
    for phase, elapsed in result.timings.items():
        print(f"  {phase}: {elapsed}s")
    for model, count in result.model_calls.items():
        print(f"  {model}: {count} calls")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="P10: Heard-Seen-Respected — Empathy & perspective translation protocol",
    )
    parser.add_argument("--question", "-q", required=True, help="Strategic challenge to explore")
    parser.add_argument(
        "--agents", "-a",
        nargs="+",
        default=["ceo", "cfo", "cto", "cmo"],
        help="Agent keys to include (default: ceo cfo cto cmo)",
    )
    parser.add_argument("--thinking-budget", type=int, default=10_000, help="Extended thinking budget")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Agent mode: research (lightweight) or production (real SDK agents)")
    parser.add_argument("--blackboard", action="store_true", help="Use blackboard-driven orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit (no LLM calls)")
    args = parser.parse_args()

    agent_dicts = build_agents(args.agents, mode=args.mode)
    agents = [AgentSpec(name=a["name"], system_prompt=a["system_prompt"]) for a in agent_dicts]

    if args.blackboard:
        from protocols.orchestrator_loop import Orchestrator
        from pathlib import Path
        from protocols.tracing import make_client
        from .protocol_def import P10_DEF

        if args.dry_run:
            print(f"[dry-run] Protocol: {P10_DEF.protocol_id}, stages: {[s.name for s in P10_DEF.stages]}")
            return

        client = make_client(protocol_id="p10_heard_seen_respected", trace=getattr(args, 'trace', False), trace_path=Path(args.trace_path) if getattr(args, 'trace_path', None) else None)
        config = {
            "client": client,
            "thinking_model": getattr(args, 'thinking_model', None),
            "orchestration_model": getattr(args, 'orchestration_model', getattr(args, 'thinking_model', None)),
            "thinking_budget": getattr(args, 'thinking_budget', 10000),
        }
        orch = Orchestrator()
        bb = asyncio.run(orch.run(P10_DEF, args.question, agents, **config))

        print("\n" + "=" * 70)
        print("HEARD-SEEN-RESPECTED RESULTS (blackboard)")
        print("=" * 70)
        synthesis = bb.read_latest("synthesis")
        if synthesis:
            print(f"\n{synthesis.content}")
        print(f"\nResources: {bb.resource_signals()}")
        return

    orchestrator = HSROrchestrator(agents=agents, thinking_budget=args.thinking_budget)
    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json:
        import json
        output = {
            "question": result.question,
            "narratives": result.narratives,
            "reflections": result.reflections,
            "common_ground": result.common_ground,
            "key_differences": result.key_differences,
            "translation_guide": result.translation_guide,
            "timings": result.timings,
            "model_calls": result.model_calls,
        }
        print(json.dumps(output, indent=2))
    else:
        print_result(result)
    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p10_heard_seen_respected",
            question=args.question,
            agent_keys=[a['name'] for a in agents],
            result=result,
            trace_id=getattr(result, '_langfuse_trace_id', None) or get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
