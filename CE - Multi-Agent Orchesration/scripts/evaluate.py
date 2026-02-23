#!/usr/bin/env python3
"""Minimal evaluation harness — runs a protocol on a benchmark question and saves output.

Usage:
    python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto
    python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto --dry-run
    python scripts/evaluate.py --protocol p16_ach --question Q4.1 --agents ceo cfo cto --thinking-model claude-sonnet-4-6
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FILE = ROOT / "benchmark-questions.json"
EVALUATIONS_DIR = ROOT / "evaluations"


def load_questions() -> dict[str, dict]:
    """Load benchmark questions keyed by id."""
    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    return {q["id"]: q for q in questions}


def build_command(
    protocol: str,
    question_text: str,
    agents: list[str],
    thinking_model: str | None,
) -> list[str]:
    """Build the subprocess command to run a protocol."""
    cmd = [
        sys.executable, "-m", f"protocols.{protocol}.run",
        "-q", question_text,
        "-a", *agents,
    ]
    if thinking_model:
        cmd.extend(["--thinking-model", thinking_model])
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a protocol on a benchmark question")
    parser.add_argument("--protocol", "-p", required=True, help="Protocol folder name (e.g. p16_ach)")
    parser.add_argument("--question", "-q", required=True, help="Question ID from benchmark-questions.json (e.g. Q4.1)")
    parser.add_argument("--agents", "-a", nargs="+", default=["ceo", "cfo", "cto", "cmo"], help="Agent keys")
    parser.add_argument("--thinking-model", default=None, help="Override the thinking model")
    parser.add_argument("--dry-run", action="store_true", help="Show the command without executing")
    parser.add_argument("--judge", action="store_true", help="Auto-run blind judge after protocol execution")
    parser.add_argument("--judge-model", default="claude-opus-4-6", help="Model for judge (default: claude-opus-4-6)")
    args = parser.parse_args()

    # Load question
    questions = load_questions()
    if args.question not in questions:
        print(f"Unknown question ID: {args.question}")
        print(f"Available: {', '.join(sorted(questions.keys()))}")
        sys.exit(1)

    q = questions[args.question]
    question_text = q["question"]

    cmd = build_command(args.protocol, question_text, args.agents, args.thinking_model)

    if args.dry_run:
        print("DRY RUN — would execute:")
        print(f"  Protocol:  {args.protocol}")
        print(f"  Question:  {args.question} ({q['problem_type']})")
        print(f"  Text:      {question_text[:100]}{'...' if len(question_text) > 100 else ''}")
        print(f"  Agents:    {', '.join(args.agents)}")
        print(f"  Model:     {args.thinking_model or '(default)'}")
        print(f"  Command:   {' '.join(cmd)}")
        return

    # Run
    print(f"Running {args.protocol} on {args.question} ({q['problem_type']})...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))

    if result.returncode != 0:
        print(f"ERROR (exit {result.returncode}):")
        print(result.stderr)
        sys.exit(result.returncode)

    # Capture output (protocols produce human-readable text, not JSON)
    output = result.stdout

    # Save
    EVALUATIONS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{args.protocol}_{args.question}_{timestamp}.json"
    outpath = EVALUATIONS_DIR / filename

    envelope = {
        "protocol": args.protocol,
        "question_id": args.question,
        "problem_type": q["problem_type"],
        "question_text": question_text,
        "agents": args.agents,
        "thinking_model": args.thinking_model,
        "timestamp": timestamp,
        "result": {"synthesis": output},
    }

    with open(outpath, "w") as f:
        json.dump(envelope, f, indent=2)

    print(f"Saved to {outpath}")

    # Auto-judge if requested
    if args.judge:
        sys.path.insert(0, str(ROOT))
        from scripts.judge import BlindJudge, _extract_response_text, save_result, print_result

        async def _run_judge():
            judge = BlindJudge(model=args.judge_model)
            response_text = _extract_response_text(envelope)
            responses = {args.protocol: response_text}
            return await judge.evaluate(responses, question_id=args.question)

        import asyncio
        print(f"\nRunning blind judge with {args.judge_model}...")
        judge_result = asyncio.run(_run_judge())
        judge_path = save_result(judge_result)
        print_result(judge_result)
        print(f"Judge results saved to {judge_path}")


if __name__ == "__main__":
    main()
