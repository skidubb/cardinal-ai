#!/usr/bin/env python3
"""Regenerate a markdown report from existing eval data JSON.

Usage:
    python examples/regenerate_report.py \
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

from ce_evals.core.models import EvalSuite
from ce_evals.core.rubric import Rubric
from ce_evals.report.markdown import MarkdownReport


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--rubric", default="rubrics/protocol_quality.yaml")
    parser.add_argument("--title", default="Protocol Evaluation: Multi-Model 5×5")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    data_path = PROJECT_ROOT / args.data
    data = json.loads(data_path.read_text())
    suites = [EvalSuite(**s) for s in data]

    rubric = Rubric.from_yaml(PROJECT_ROOT / args.rubric)
    report = MarkdownReport(rubric)
    md = report.render(suites, title=args.title)

    out_path = Path(args.output) if args.output else (
        PROJECT_ROOT / "research" / "reports" / f"{data_path.stem}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"Report saved to: {out_path}")


if __name__ == "__main__":
    main()
