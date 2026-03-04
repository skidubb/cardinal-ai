#!/usr/bin/env python3
"""Run one emergence comparison pair end-to-end.

Usage:
    python scripts/run_pair.py --pair 4 --agents ceo cfo cto cmo --dry-run
    python scripts/run_pair.py --pair 4 --agents ceo cfo cto cmo
    python scripts/run_pair.py --pair 7 --agents ceo cfo cto cmo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from protocols.agents import build_agents
from protocols.llm import set_no_tools
from scripts.emergence import EmergenceDetector, save_emergence_result
from scripts.pairs_config import PAIRS_BY_ID, get_pair_questions
from protocols.config import THINKING_MODEL

EVALUATIONS_DIR = ROOT / "evaluations"

# Result text extraction keys (tried in order)
_TEXT_KEYS = ("synthesis", "final_synthesis", "sublation", "output", "response", "result")


def _extract_text(result_obj) -> str:
    """Extract primary text from a protocol result dataclass."""
    d = asdict(result_obj) if hasattr(result_obj, "__dataclass_fields__") else result_obj
    for key in _TEXT_KEYS:
        if key in d and isinstance(d[key], str) and d[key].strip():
            return d[key]
    return json.dumps(d, indent=2, default=str)


def _get_orchestrator(protocol: str, agents: list[dict], thinking_model: str):
    """Dynamically import and instantiate a protocol orchestrator."""
    if protocol == "p06_triz":
        from protocols.p06_triz.orchestrator import TRIZOrchestrator
        return TRIZOrchestrator(agents=agents, thinking_model=thinking_model)

    if protocol == "p03_parallel_synthesis":
        from protocols.p03_parallel_synthesis.orchestrator import SynthesisOrchestrator
        return SynthesisOrchestrator(agents=agents, thinking_model=thinking_model)

    if protocol == "p04_multi_round_debate":
        from protocols.p04_multi_round_debate.orchestrator import DebateOrchestrator
        return DebateOrchestrator(agents=agents, rounds=3, thinking_model=thinking_model)

    if protocol == "p14_one_two_four_all":
        from protocols.p14_one_two_four_all.orchestrator import (
            AgentSpec,
            OneTwoFourAllOrchestrator,
        )
        agent_specs = [AgentSpec(name=a["name"], system_prompt=a["system_prompt"]) for a in agents]
        return OneTwoFourAllOrchestrator(agents=agent_specs, thinking_model=thinking_model)

    if protocol == "p17_red_blue_white":
        from protocols.p17_red_blue_white.orchestrator import RedBlueWhiteOrchestrator
        # Split agents: first half red, second half blue, last one white
        n = len(agents)
        mid = max(1, n // 2)
        return RedBlueWhiteOrchestrator(
            red_agents=agents[:mid],
            blue_agents=agents[mid : max(mid + 1, n - 1)],
            white_agent=agents[-1],
            thinking_model=thinking_model,
        )

    if protocol == "p37_hegel_sublation":
        from protocols.p37_hegel_sublation.orchestrator import SublationOrchestrator
        return SublationOrchestrator(agents=agents, thinking_model=thinking_model)

    # Generic import fallback
    import importlib
    mod = importlib.import_module(f"protocols.{protocol}.orchestrator")
    # Find the orchestrator class (first class ending in "Orchestrator")
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if isinstance(obj, type) and attr_name.endswith("Orchestrator"):
            try:
                return obj(agents=agents, thinking_model=thinking_model)
            except TypeError:
                return obj(thinking_model=thinking_model)
    raise ValueError(f"No orchestrator found in protocols.{protocol}.orchestrator")


async def _run_protocol(protocol: str, question: str, agents: list[dict], thinking_model: str) -> str:
    """Run a protocol and return its primary text output."""
    orch = _get_orchestrator(protocol, agents, thinking_model)

    if protocol == "p17_red_blue_white":
        # P17 needs a plan — generate one with P03 first
        from protocols.p03_parallel_synthesis.orchestrator import SynthesisOrchestrator
        synth = SynthesisOrchestrator(agents=agents, thinking_model=thinking_model)
        plan_result = await synth.run(question)
        plan_text = _extract_text(plan_result)
        result = await orch.run(question, plan_text)
    else:
        result = await orch.run(question)

    return _extract_text(result)


def _save_output(protocol: str, qid: str, question_text: str, output: str, agents_names: list[str]) -> Path:
    """Save protocol output in standard JSON envelope."""
    EVALUATIONS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{protocol}_{qid}_{ts}.json"
    outpath = EVALUATIONS_DIR / filename
    envelope = {
        "protocol": protocol,
        "question_id": qid,
        "question_text": question_text,
        "agents": agents_names,
        "timestamp": ts,
        "result": {"synthesis": output},
    }
    outpath.write_text(json.dumps(envelope, indent=2))
    return outpath


async def run_pair(pair_id: int, agent_names: list[str], thinking_model: str) -> None:
    pair = PAIRS_BY_ID[pair_id]
    questions = get_pair_questions(pair)
    agents = build_agents(agent_names)

    set_no_tools(True)

    detector = EmergenceDetector()

    for q in questions:
        qid = q["id"]
        question_text = q["question"]
        print(f"\n{'='*60}")
        print(f"  {qid}: {question_text[:80]}...")
        print(f"  Complex: {pair.complex_protocol}  |  Baseline: {pair.baseline_protocol}")
        print(f"{'='*60}")

        # Run complex protocol
        print(f"  Running {pair.complex_protocol}...")
        complex_output = await _run_protocol(pair.complex_protocol, question_text, agents, thinking_model)
        complex_path = _save_output(pair.complex_protocol, qid, question_text, complex_output, agent_names)
        print(f"  Saved: {complex_path.name}")

        # Run baseline protocol
        print(f"  Running {pair.baseline_protocol}...")
        baseline_output = await _run_protocol(pair.baseline_protocol, question_text, agents, thinking_model)
        baseline_path = _save_output(pair.baseline_protocol, qid, question_text, baseline_output, agent_names)
        print(f"  Saved: {baseline_path.name}")

        # Run emergence detection
        print("  Running emergence detection...")
        result = await detector.detect(
            complex_output=complex_output,
            baseline_output=baseline_output,
            question=question_text,
            complex_protocol=pair.complex_protocol,
            baseline_protocol=pair.baseline_protocol,
            question_id=qid,
        )
        epath = save_emergence_result(result, pair_id)
        print(f"  Emergence: {result.zone_transition} | Saved: {epath.name}")
        indicators = [k for k, v in result.coordination_indicators.items() if v]
        if indicators:
            print(f"  Coordination: {', '.join(indicators)}")


def dry_run(pair_id: int, agent_names: list[str]) -> None:
    pair = PAIRS_BY_ID[pair_id]
    questions = get_pair_questions(pair)

    print(f"DRY RUN — Pair {pair_id}")
    print(f"  Complex:  {pair.complex_protocol}")
    print(f"  Baseline: {pair.baseline_protocol}")
    print(f"  Rationale: {pair.rationale}")
    print(f"  Agents:   {', '.join(agent_names)}")
    print("  Questions:")
    for q in questions:
        print(f"    {q['id']}: {q['question'][:80]}{'...' if len(q['question']) > 80 else ''}")
        print(f"         type={q['problem_type']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one emergence comparison pair")
    parser.add_argument("--pair", "-p", type=int, required=True, help="Pair ID (1-10)")
    parser.add_argument("--agents", "-a", nargs="+", default=["ceo", "cfo", "cto", "cmo"])
    parser.add_argument("--thinking-model", default=THINKING_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.pair not in PAIRS_BY_ID:
        print(f"Unknown pair ID: {args.pair}. Available: {sorted(PAIRS_BY_ID.keys())}")
        sys.exit(1)

    if args.dry_run:
        dry_run(args.pair, args.agents)
        return

    asyncio.run(run_pair(args.pair, args.agents, args.thinking_model))


if __name__ == "__main__":
    main()
