#!/usr/bin/env python3
"""Evaluation harness — runs a protocol in-process on a benchmark question,
captures the Langfuse trace_id, links it to the dataset item, and saves output.

Usage:
    python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
    python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto --dry-run
    python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto --thinking-model claude-sonnet-4-6
    python scripts/evaluate.py --protocol p06_triz --question Q4.1 --agents ceo cfo cto --no-dataset
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from protocols.agents import BUILTIN_AGENTS
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.langfuse_tracing import (
    get_trace_id,
    is_enabled as langfuse_is_enabled,
    link_trace_to_dataset_item,
    score_trace,
)

BENCHMARK_FILE = ROOT / "benchmark-questions.json"
EVALUATIONS_DIR = ROOT / "evaluations"
DATASET_NAME = "coordination-lab-benchmarks"


def load_questions() -> dict[str, dict]:
    """Load benchmark questions keyed by id."""
    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    return {q["id"]: q for q in questions}


def _load_orchestrator_class(protocol_key: str):
    """Dynamically import and return the orchestrator class for a protocol."""
    import importlib
    import re

    protocols_dir = ROOT / "protocols"
    orch_file = protocols_dir / protocol_key / "orchestrator.py"
    if not orch_file.exists():
        raise ValueError(f"No orchestrator.py found for protocol: {protocol_key}")

    text = orch_file.read_text()
    match = re.search(r"class (\w+Orchestrator)", text)
    if not match:
        raise ValueError(f"No Orchestrator class found in {orch_file}")

    module = importlib.import_module(f"protocols.{protocol_key}.orchestrator")
    return getattr(module, match.group(1))


def _resolve_agents(agent_keys: list[str]) -> list[dict]:
    """Build agent dicts from the shared registry."""
    agents = []
    for key in agent_keys:
        if key in BUILTIN_AGENTS:
            a = BUILTIN_AGENTS[key]
            agents.append({
                "name": a["name"],
                "system_prompt": a["system_prompt"],
            })
        else:
            agents.append({"name": key, "system_prompt": f"You are {key}."})
    return agents


async def run_protocol(
    protocol_key: str,
    question_text: str,
    agent_keys: list[str],
    thinking_model: str,
    orchestration_model: str,
):
    """Run a protocol in-process and return (result, trace_id)."""
    OrchestratorClass = _load_orchestrator_class(protocol_key)
    agents = _resolve_agents(agent_keys)

    kwargs: dict = {
        "agents": agents,
        "thinking_model": thinking_model,
        "orchestration_model": orchestration_model,
    }

    orchestrator = OrchestratorClass(**kwargs)
    result = await orchestrator.run(question_text)

    # Retrieve trace_id — stashed on result by @trace_protocol decorator,
    # or fall back to context var (still set if we're in the same task)
    trace_id = getattr(result, "_langfuse_trace_id", None) or get_trace_id()

    return result, trace_id


def _result_to_text(result) -> str:
    """Extract a text summary from any protocol result object."""
    if hasattr(result, "synthesis") and result.synthesis:
        return result.synthesis
    if hasattr(result, "final_synthesis") and result.final_synthesis:
        return result.final_synthesis
    if hasattr(result, "summary") and result.summary:
        return result.summary
    return str(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a protocol on a benchmark question")
    parser.add_argument("--protocol", "-p", required=True, help="Protocol folder name (e.g. p16_ach)")
    parser.add_argument("--question", "-q", required=True, help="Question ID from benchmark-questions.json (e.g. Q4.1)")
    parser.add_argument("--agents", "-a", nargs="+", default=["ceo", "cfo", "cto", "cmo"], help="Agent keys")
    parser.add_argument("--thinking-model", default=None, help="Override the thinking model")
    parser.add_argument("--orchestration-model", default=None, help="Override the orchestration model")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--no-dataset", action="store_true", help="Skip Langfuse dataset linking")
    parser.add_argument("--dataset-name", default=DATASET_NAME, help="Langfuse dataset name")
    parser.add_argument("--judge", action="store_true", help="Auto-run blind judge after protocol execution")
    parser.add_argument("--judge-model", default=THINKING_MODEL, help="Model for judge (default: claude-opus-4-6)")
    args = parser.parse_args()

    # Load question
    questions = load_questions()
    if args.question not in questions:
        print(f"Unknown question ID: {args.question}")
        print(f"Available: {', '.join(sorted(questions.keys()))}")
        sys.exit(1)

    q = questions[args.question]
    question_text = q["question"]
    thinking_model = args.thinking_model or THINKING_MODEL
    orchestration_model = args.orchestration_model or ORCHESTRATION_MODEL

    if args.dry_run:
        print("DRY RUN — would execute:")
        print(f"  Protocol:            {args.protocol}")
        print(f"  Question:            {args.question} ({q['problem_type']})")
        print(f"  Text:                {question_text[:100]}{'...' if len(question_text) > 100 else ''}")
        print(f"  Agents:              {', '.join(args.agents)}")
        print(f"  Thinking model:      {thinking_model}")
        print(f"  Orchestration model: {orchestration_model}")
        print(f"  Dataset linking:     {'disabled' if args.no_dataset else args.dataset_name}")
        print(f"  Langfuse enabled:    {langfuse_is_enabled()}")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"Running {args.protocol} on {args.question} ({q['problem_type']})...")

    # Run protocol in-process
    result, trace_id = asyncio.run(
        run_protocol(args.protocol, question_text, args.agents, thinking_model, orchestration_model)
    )

    output_text = _result_to_text(result)
    print(f"Protocol complete. Trace ID: {trace_id or 'none'}")

    # Link trace to Langfuse dataset item
    if not args.no_dataset and trace_id and langfuse_is_enabled():
        run_name = f"{args.protocol}_{timestamp}"
        link_trace_to_dataset_item(
            dataset_name=args.dataset_name,
            item_id=args.question,
            trace_id=trace_id,
            run_name=run_name,
            run_metadata={
                "agents": args.agents,
                "thinking_model": thinking_model,
                "orchestration_model": orchestration_model,
                "question_id": args.question,
                "problem_type": q["problem_type"],
            },
        )
        print(f"Linked trace to dataset item {args.question} (run: {run_name})")

    # Save local JSON
    EVALUATIONS_DIR.mkdir(exist_ok=True)
    filename = f"{args.protocol}_{args.question}_{timestamp}.json"
    outpath = EVALUATIONS_DIR / filename

    envelope = {
        "protocol": args.protocol,
        "question_id": args.question,
        "problem_type": q["problem_type"],
        "question_text": question_text,
        "agents": args.agents,
        "thinking_model": thinking_model,
        "orchestration_model": orchestration_model,
        "timestamp": timestamp,
        "trace_id": trace_id,
        "result": {"synthesis": output_text},
    }

    with open(outpath, "w") as f:
        json.dump(envelope, f, indent=2)

    print(f"Saved to {outpath}")

    # Auto-judge if requested
    if args.judge:
        from scripts.judge import BlindJudge, _extract_response_text, save_result, print_result

        async def _run_judge():
            judge = BlindJudge(model=args.judge_model)
            response_text = _extract_response_text(envelope)
            responses = {args.protocol: response_text}
            return await judge.evaluate(responses, question_id=args.question)

        print(f"\nRunning blind judge with {args.judge_model}...")
        judge_result = asyncio.run(_run_judge())

        # Score the trace with judge results
        if trace_id and langfuse_is_enabled():
            for dim in ("completeness", "consistency", "actionability", "overall"):
                val = judge_result.get(dim) if isinstance(judge_result, dict) else getattr(judge_result, dim, None)
                if val is not None:
                    score_trace(f"judge_{dim}", float(val), trace_id=trace_id)

        judge_path = save_result(judge_result)
        print_result(judge_result)
        print(f"Judge results saved to {judge_path}")


if __name__ == "__main__":
    main()
