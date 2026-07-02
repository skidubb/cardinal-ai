#!/usr/bin/env python3
"""CLI for the Adaptive Router.

Flow:
  1. Classify the question via P0a
  2. Resolve recommendation against capability.yaml + safety rails
  3. Print decision
  4. If --auto-execute (default), invoke the chosen protocol via its run.py
     programmatically. If --dry-run, stop after printing.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from typing import Any

from .orchestrator import AdaptiveRouterOrchestrator, RouterDecision
from .resolver import Resolver, DEFAULT_AGENTS


# ── Pretty-printing ──────────────────────────────────────────────────────────


def _print_decision(d: RouterDecision) -> None:
    bar = "─" * 60
    print(f"\n╭{bar}╮")
    print("│ ROUTER DECISION")
    print(f"├{bar}┤")
    print(f"│ Question:       {d.question}")
    print(f"│ Problem type:   {d.problem_type}")
    print(f"│ Confidence:     {d.confidence}% ({d.tier})")
    if d.plan:
        print(f"│ Recommended:    {d.plan.protocol_id} — {d.plan.name}")
        print(f"│ Protocol key:   {d.plan.protocol_key}")
        print(f"│ Cost tier:      {d.plan.cost_tier}")
        print(f"│ Agents:         {', '.join(d.plan.agent_keys)}")
    else:
        print("│ Plan:           NONE (no routable candidate)")
    print(f"│ Auto-execute:   {d.auto_executable}")
    print(f"│ Reasoning:      {d.reasoning}")
    if d.adjustments:
        print("│ Adjustments:")
        for a in d.adjustments:
            print(f"│   • {a}")
    alts = d.raw_router.get("alternatives", [])
    if alts:
        print("│ Alternatives considered:")
        for alt in alts[:3]:
            print(f"│   • {alt['protocol']} — {alt['name']}")
    print(f"╰{bar}╯\n")


# ── Protocol execution (reuses existing per-protocol CLI entrypoints) ───────


async def _execute_plan(decision: RouterDecision, rounds: int | None) -> None:
    """Run the chosen protocol by invoking its orchestrator directly.

    We avoid shelling out to each protocol's run.py so we stay in-process and
    share the same event loop. Uses the dynamic orchestrator discovery already
    used by api/runner.py.
    """
    assert decision.plan is not None
    plan = decision.plan

    # Mirror api/runner.py's discovery pattern, but don't pull in FastAPI deps.
    OrchestratorClass = _load_orchestrator_class(plan.protocol_key)

    # Build ServerAgent instances the same way CLIs do.
    try:
        from protocols.agent_provider import build_production_agents
        agents: Any = build_production_agents(plan.agent_keys)
    except Exception as exc:
        print(f"[adaptive-router] could not build production agents: {exc}", file=sys.stderr)
        print("[adaptive-router] falling back to research-mode dicts", file=sys.stderr)
        agents = [{"name": k, "system_prompt": f"You are {k}."} for k in plan.agent_keys]

    orch = OrchestratorClass()

    # Protocols have heterogeneous run() signatures. Inspect and call appropriately.
    import inspect
    sig = inspect.signature(orch.run)
    kwargs: dict[str, Any] = {}
    if "question" in sig.parameters:
        question_arg = (decision.question,)
    else:
        question_arg = ()
    if "agents" in sig.parameters:
        kwargs["agents"] = agents
    if "rounds" in sig.parameters and rounds is not None:
        kwargs["rounds"] = rounds

    print(f"[adaptive-router] executing {plan.protocol_key} …\n")
    result = await orch.run(*question_arg, **kwargs)

    # Best-effort pretty dump
    print("─── PROTOCOL RESULT ───")
    _try_print_result(result)


def _load_orchestrator_class(protocol_key: str):
    """Find the *Orchestrator class in protocols/<key>/orchestrator.py."""
    from pathlib import Path
    import re

    orch_file = (
        Path(__file__).resolve().parent.parent / protocol_key / "orchestrator.py"
    )
    text = orch_file.read_text()
    match = re.search(r"class (\w+Orchestrator)", text) or re.search(
        r"class (\w+Router)", text
    )
    if not match:
        raise RuntimeError(f"No orchestrator class found in {orch_file}")
    module = importlib.import_module(f"protocols.{protocol_key}.orchestrator")
    return getattr(module, match.group(1))


def _try_print_result(result: Any) -> None:
    try:
        from dataclasses import asdict, is_dataclass
        if is_dataclass(result):
            print(json.dumps(asdict(result), indent=2, default=str))
            return
    except Exception:
        pass
    print(result)


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Adaptive Router — classify a question, pick a protocol, execute it."
        )
    )
    parser.add_argument("--question", "-q", required=True, help="Strategic question.")
    parser.add_argument(
        "--agents",
        "-a",
        nargs="*",
        default=None,
        help=f"Optional agent keys (default {list(DEFAULT_AGENTS)} if protocol allows).",
    )
    parser.add_argument(
        "--max-cost-tier",
        choices=["low", "medium", "high"],
        default="medium",
        help="Do not route to protocols above this cost tier (default: medium).",
    )
    parser.add_argument(
        "--high-threshold",
        type=int,
        default=80,
        help="Confidence ≥ this triggers auto-execute (default: 80).",
    )
    parser.add_argument(
        "--mid-threshold",
        type=int,
        default=50,
        help="Confidence < this refuses execution (default: 50).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Optional rounds for multi-round protocols.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show decision only; do not execute the chosen protocol.",
    )
    parser.add_argument(
        "--require-confirm",
        action="store_true",
        help="Ask before running, even at high confidence.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the router decision as JSON (stdout) and skip execution.",
    )
    args = parser.parse_args()

    orchestrator = AdaptiveRouterOrchestrator(
        resolver=Resolver(max_cost_tier=args.max_cost_tier),
        high_threshold=args.high_threshold,
        mid_threshold=args.mid_threshold,
    )

    decision = asyncio.run(
        orchestrator.decide(
            args.question,
            requested_agents=args.agents,
        )
    )

    if args.json:
        print(json.dumps(decision.to_dict(), indent=2, default=str))
        return

    _print_decision(decision)

    if args.dry_run:
        return

    if decision.plan is None:
        print("[adaptive-router] no routable protocol — exiting.")
        sys.exit(2)

    if decision.tier == "low":
        print(
            "[adaptive-router] confidence too low to auto-execute. "
            "Re-run with a clearer question, or pick a protocol manually."
        )
        sys.exit(3)

    if args.require_confirm or decision.tier == "mid":
        prompt = (
            f"Run {decision.plan.protocol_id} ({decision.plan.name}) "
            f"with agents {decision.plan.agent_keys}? [y/N] "
        )
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("y", "yes"):
            print("[adaptive-router] aborted by user.")
            return

    asyncio.run(_execute_plan(decision, rounds=args.rounds))


if __name__ == "__main__":
    main()
