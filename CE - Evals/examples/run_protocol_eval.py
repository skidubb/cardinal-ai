#!/usr/bin/env python3
"""Run protocol evaluation batches with blind judging.

Usage:
    # Single question (original mode):
    python examples/run_protocol_eval.py \
        --protocols p16_ach p03_structured_debate \
        --questions Q4.1 \
        --rubric rubrics/protocol_quality.yaml

    # Batch mode (multiple questions, auto-injects P03 anchor):
    python examples/run_protocol_eval.py \
        --protocols p16_ach p17_red_blue_white \
        --questions Q2.1 Q2.2 Q2.3 \
        --anchor p03_structured_debate \
        --replications 1

    # Dry run:
    python examples/run_protocol_eval.py \
        --protocols p16_ach p17_red_blue_white \
        --questions Q2.1 Q2.2 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Adjust these paths to your local layout — try with and without trailing space
_candidates = [
    Path(__file__).resolve().parent.parent.parent / "CE - Multi-Agent ",
    Path(__file__).resolve().parent.parent.parent / "CE - Multi-Agent",
]
MULTI_AGENT_ROOT = next((p for p in _candidates if p.exists()), _candidates[0])
BENCHMARK_FILE = MULTI_AGENT_ROOT / "benchmark-questions.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_questions() -> dict[str, dict]:
    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    return {q["id"]: q for q in questions}


def _build_protocol_cmd(
    protocol: str,
    question_text: str,
    agents: list[str],
    thinking_model: str | None = None,
) -> list[str]:
    """Build the CLI command for a given protocol, handling per-protocol arg differences."""
    base = [sys.executable, "-m", f"protocols.{protocol}.run", "-q", question_text]

    if protocol == "p17_red_blue_white":
        # Needs --plan (use the question as the plan to stress-test) and role-based teams
        plan = f"Proposed strategy in response to: {question_text}"
        red = agents[:2] if len(agents) >= 2 else agents[:1]
        blue = agents[2:4] if len(agents) >= 4 else agents[-2:]
        white = agents[-1] if agents else "ceo"
        base.extend(["--plan", plan, "--red", *red, "--blue", *blue, "--white", white, "--json"])
    elif protocol == "p20_borda_count":
        # Needs --options (generate plausible strategic options from the question)
        options = [
            "Aggressive expansion",
            "Defensive consolidation",
            "Strategic pivot",
            "Measured hybrid approach",
        ]
        base.extend(["-a", *agents, "--options", *options, "--json"])
    elif protocol in ("p03_parallel_synthesis", "p04_multi_round_debate"):
        # Support -a but no --json; capture stdout directly
        base.extend(["-a", *agents])
    else:
        # Standard protocols (p16_ach, etc.)
        base.extend(["-a", *agents, "--json"])

    if thinking_model:
        base.extend(["--thinking-model", thinking_model])
    return base


def make_protocol_runner(
    protocol: str,
    agents: list[str],
    thinking_model: str | None = None,
):
    """Return a callable(question_text) -> output_text for a protocol."""

    def run(question_text: str) -> str:
        cmd = _build_protocol_cmd(protocol, question_text, agents, thinking_model)

        max_attempts = 3
        delays = [2, 4, 8]
        last_error = ""

        for attempt in range(max_attempts):
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    cwd=str(MULTI_AGENT_ROOT), timeout=600,
                )
            except subprocess.TimeoutExpired:
                last_error = f"[ERROR] {protocol} timed out after 600s (attempt {attempt + 1}/{max_attempts})"
                if attempt < max_attempts - 1:
                    logger.warning(f"    {last_error} — retrying in {delays[attempt]}s...")
                    time.sleep(delays[attempt])
                    continue
                return last_error

            if result.returncode != 0:
                last_error = f"[ERROR] {protocol} failed (attempt {attempt + 1}/{max_attempts}): {result.stderr[:2000]}"
                if attempt < max_attempts - 1:
                    logger.warning(f"    {last_error} — retrying in {delays[attempt]}s...")
                    time.sleep(delays[attempt])
                    continue
                return last_error

            try:
                data = json.loads(result.stdout)
                return data.get("result", data.get("output", json.dumps(data, indent=2)))
            except json.JSONDecodeError:
                return result.stdout

        return last_error

    return run


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run protocol eval batch")
    parser.add_argument("--protocols", "-p", nargs="+", required=True)
    parser.add_argument(
        "--questions", "-q", nargs="+", required=True,
        help="Question IDs (e.g. Q2.1 Q2.2 Q2.3)",
    )
    parser.add_argument("--rubric", "-r", default="rubrics/protocol_quality.yaml")
    parser.add_argument("--agents", "-a", nargs="+", default=["ceo", "cfo", "cto", "cmo"])
    parser.add_argument(
        "--anchor", default=None,
        help="Anchor protocol to include in every batch (e.g. p03_structured_debate)",
    )
    parser.add_argument("--replications", type=int, default=1, help="Repeat each question N times")
    parser.add_argument("--thinking-model", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument(
        "--judge-models", nargs="+", default=None,
        help="Multiple judge models for inter-rater agreement (e.g. claude-opus-4-6 gpt-5.2 gemini-3.1-pro-preview)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", "-o", default=None, help="Output report path")
    parser.add_argument("--session-label", default=None, help="Label for filenames (e.g. adversarial)")
    args = parser.parse_args()

    all_questions = load_questions()

    # Validate question IDs
    question_list: list[tuple[str, str]] = []
    for qid in args.questions:
        if qid not in all_questions:
            print(f"Unknown question: {qid}")
            print(f"Available: {', '.join(sorted(all_questions))}")
            sys.exit(1)
        question_list.append((qid, all_questions[qid]["question"]))

    # Build protocol set (inject anchor if not already present)
    protocol_names = list(args.protocols)
    if args.anchor and args.anchor not in protocol_names:
        protocol_names.append(args.anchor)

    print(f"Questions: {', '.join(args.questions)}")
    print(f"Protocols: {', '.join(protocol_names)}")
    print(f"Replications: {args.replications}")
    print(f"Rubric: {args.rubric}")
    if args.anchor:
        print(f"Anchor: {args.anchor}")
    if args.judge_models:
        print(f"Judge models: {', '.join(args.judge_models)}")
    elif args.judge_model:
        print(f"Judge model: {args.judge_model}")

    if args.dry_run:
        total_runs = len(question_list) * len(protocol_names) * args.replications
        print(f"\nDRY RUN — would execute {total_runs} protocol runs + {len(question_list) * args.replications} judge calls.")
        return

    from ce_evals.core.rubric import Rubric
    from ce_evals.core.runner import EvalRunner
    from ce_evals.report.markdown import MarkdownReport

    rubric = Rubric.from_yaml(PROJECT_ROOT / args.rubric)
    runner = EvalRunner(rubric, judge_model=args.judge_model, judge_models=args.judge_models)

    candidates = {
        proto: make_protocol_runner(proto, args.agents, args.thinking_model)
        for proto in protocol_names
    }

    suites = runner.run_batch(question_list, candidates, replications=args.replications)

    # Generate report
    label = args.session_label or "_".join(args.questions)
    report = MarkdownReport(rubric)
    md = report.render(
        suites,
        title=f"Protocol Evaluation: {label}",
    )

    # Save
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.output) if args.output else (
        PROJECT_ROOT / "research" / "reports" / f"eval_{label}_{timestamp}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"\nReport saved to: {out_path}")

    # Save raw data (all suites)
    data_path = PROJECT_ROOT / "research" / "data" / f"eval_{label}_{timestamp}.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    raw_data = [s.model_dump() for s in suites]
    data_path.write_text(json.dumps(raw_data, indent=2))
    print(f"Data saved to: {data_path}")


if __name__ == "__main__":
    main()
