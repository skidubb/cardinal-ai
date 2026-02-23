#!/usr/bin/env python3
"""Re-run failed protocol×question combos and merge into existing eval data.

Usage:
    python examples/rerun_failed.py \
        --data research/data/eval_multi_model_5x5_20260222_224020.json \
        --rubric rubrics/protocol_quality.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_protocol_eval import (
    MULTI_AGENT_ROOT,
    load_questions,
    make_protocol_runner,
)


def find_failed(data: list[dict]) -> list[tuple[str, str, str]]:
    """Return (question_id, question_text, protocol_name) for failed runs."""
    failed = []
    for suite in data:
        qid = suite["question_id"]
        qtxt = suite["question_text"]
        for name, cr in suite["candidates"].items():
            if cr["output_text"].startswith("[ERROR]"):
                failed.append((qid, qtxt, name))
    return failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to existing eval JSON")
    parser.add_argument("--rubric", default="rubrics/protocol_quality.yaml")
    parser.add_argument("--agents", nargs="+", default=["ceo", "cfo", "cto", "cmo"])
    parser.add_argument(
        "--judge-models", nargs="+",
        default=["claude-opus-4-6", "gpt-5.2", "gemini-3.1-pro-preview"],
    )
    parser.add_argument("--title", default=None, help="Report title (default: derived from data filename)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data_path = PROJECT_ROOT / args.data
    data = json.loads(data_path.read_text())

    failed = find_failed(data)
    if not failed:
        print("No failed runs found!")
        return

    print(f"Found {len(failed)} failed runs:")
    for qid, _, proto in failed:
        print(f"  {proto} × {qid}")

    if args.dry_run:
        return

    from ce_evals.core.judge import BlindJudge
    from ce_evals.core.models import CandidateResult, EvalSuite
    from ce_evals.core.rubric import Rubric
    from ce_evals.report.markdown import MarkdownReport

    rubric = Rubric.from_yaml(PROJECT_ROOT / args.rubric)

    # Re-run each failed combo
    import time

    for qid, qtxt, proto in failed:
        print(f"\nRe-running {proto} × {qid}...")
        runner_fn = make_protocol_runner(proto, args.agents)
        start = time.time()
        output = runner_fn(qtxt)
        duration = time.time() - start

        wc = len(output.split())
        is_error = output.startswith("[ERROR]")
        print(f"  Result: {wc} words, error={is_error}")

        if is_error:
            print(f"  Still failing! {output[:200]}")
            continue

        # Find the suite and replace the failed candidate
        for suite in data:
            if suite["question_id"] == qid and proto in suite["candidates"]:
                suite["candidates"][proto] = CandidateResult(
                    name=proto,
                    output_text=output,
                    duration_seconds=duration,
                ).model_dump()

                # Re-judge this entire suite with all candidates
                print(f"  Re-judging {qid} with all candidates...")
                judge = BlindJudge(rubric, judge_models=args.judge_models)
                responses = {
                    name: cr["output_text"]
                    for name, cr in suite["candidates"].items()
                }
                judgment, per_judge = judge.evaluate(responses, question=qtxt)
                suite["judgment"] = judgment.model_dump()
                suite["per_judge_results"] = [jr.model_dump() for jr in per_judge]
                break

    # Save updated data
    data_path.write_text(json.dumps(data, indent=2))
    print(f"\nUpdated data saved to: {data_path}")

    # Regenerate report
    suites = [EvalSuite(**s) for s in data]
    report = MarkdownReport(rubric)
    title = args.title or f"Protocol Evaluation: {data_path.stem.replace('eval_', '').replace('_', ' ')}"
    md = report.render(suites, title=title)

    report_path = PROJECT_ROOT / "research" / "reports" / f"{data_path.stem}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md)
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
