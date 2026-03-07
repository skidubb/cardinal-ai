#!/usr/bin/env python3
"""Upload benchmark questions to Langfuse as a dataset.

Idempotent — safe to re-run. Uses question IDs as dataset item IDs
so duplicates are impossible.

Usage:
    python scripts/upload_benchmark_dataset.py
    python scripts/upload_benchmark_dataset.py --name my-custom-dataset
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from protocols.langfuse_tracing import (
    create_dataset,
    create_dataset_item,
    flush,
    is_enabled,
)

BENCHMARK_FILE = ROOT / "benchmark-questions.json"
DEFAULT_DATASET_NAME = "coordination-lab-benchmarks"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload benchmark questions to Langfuse dataset")
    parser.add_argument("--name", default=DEFAULT_DATASET_NAME, help="Dataset name")
    parser.add_argument("--file", default=str(BENCHMARK_FILE), help="Path to benchmark JSON")
    args = parser.parse_args()

    if not is_enabled():
        print("Langfuse is not configured (LANGFUSE_SECRET_KEY not set). Exiting.")
        sys.exit(1)

    with open(args.file) as f:
        questions = json.load(f)

    print(f"Creating dataset '{args.name}' with {len(questions)} items...")

    ds = create_dataset(
        name=args.name,
        description=f"{len(questions)} benchmark questions across 8 problem types",
        metadata={"source": "benchmark-questions.json", "version": "v1"},
    )
    if ds is None:
        print("Failed to create dataset. Check Langfuse configuration.")
        sys.exit(1)

    created = 0
    for q in questions:
        item = create_dataset_item(
            dataset_name=args.name,
            input={
                "question_id": q["id"],
                "question": q["question"],
                "problem_type": q["problem_type"],
            },
            metadata={
                "phase": q.get("phase"),
                "source": q.get("source"),
            },
            item_id=q["id"],
        )
        status = "ok" if item else "FAILED"
        print(f"  {q['id']:6s} ({q['problem_type']:20s}) ... {status}")
        if item:
            created += 1

    flush()
    print(f"\nDone. {created}/{len(questions)} items uploaded to '{args.name}'.")


if __name__ == "__main__":
    main()
