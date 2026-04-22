#!/usr/bin/env python3
"""Backfill the `runs` table from Blackboard audit logs.

One-shot script to reconstruct Run rows from `smoke-tests/p*_<run_id>.jsonl`
files that were written before `persist_run()` was healthy end-to-end.

Sets source='backfill' so they're distinguishable from live runs.
Skips any file whose run_id already has a row in `runs`.

Usage:
    cd "CE - Multi-Agent Orchestration" && source venv/bin/activate
    python scripts/backfill_runs_from_jsonl.py [--dry-run] [DIR]

Default DIR is `smoke-tests/`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ce_shared.env import find_and_load_dotenv

find_and_load_dotenv()

from ce_db import AgentOutput, Run, get_session  # noqa: E402
from sqlalchemy import select  # noqa: E402


FILENAME_RE = re.compile(r"^(p\d+_[a-z_]+)_([0-9a-f]{8,})\.jsonl$")


def parse_jsonl(path: Path) -> dict | None:
    """Extract what we need to synthesize a Run row from a Blackboard audit log."""
    m = FILENAME_RE.match(path.name)
    if not m:
        return None
    protocol_key, short_run_id = m.group(1), m.group(2)

    entries: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return None

    # Question — from the `question` topic (first match)
    question = "(unknown)"
    for e in entries:
        if e.get("topic") == "question":
            c = e.get("content")
            if isinstance(c, str):
                question = c
            break

    # Agents — distinct authors that are not 'system'
    agents = sorted(
        {e.get("author") for e in entries if e.get("author") and e.get("author") != "system"}
    )

    # Timestamps
    timestamps = [e.get("timestamp") for e in entries if isinstance(e.get("timestamp"), (int, float))]
    started_ts = min(timestamps) if timestamps else None
    completed_ts = max(timestamps) if timestamps else None

    # Final report or last synthesis entry, if present
    result_summary = ""
    for e in reversed(entries):
        if e.get("topic") in ("final_report", "consensus", "convergence_report", "tally"):
            c = e.get("content")
            if isinstance(c, str):
                result_summary = c[:1000]
            else:
                result_summary = json.dumps(c)[:1000]
            break

    return {
        "protocol_key": protocol_key,
        "short_run_id": short_run_id,
        "question": question,
        "agents": agents,
        "started_at": datetime.fromtimestamp(started_ts, tz=timezone.utc) if started_ts else None,
        "completed_at": datetime.fromtimestamp(completed_ts, tz=timezone.utc) if completed_ts else None,
        "result_summary": result_summary,
        "entries": entries,
        "path": str(path),
    }


async def backfill(dir_path: Path, dry_run: bool = False) -> None:
    files = sorted(dir_path.glob("p*.jsonl"))
    print(f"Found {len(files)} jsonl files in {dir_path}")

    summaries = [parse_jsonl(f) for f in files]
    summaries = [s for s in summaries if s is not None]
    print(f"Parsed {len(summaries)} audit logs cleanly")

    async with get_session() as session:
        existing_markers = (
            await session.execute(
                select(Run.result_json).where(Run.source == "backfill")
            )
        ).scalars().all()
        already_backfilled = set()
        for rj in existing_markers:
            if isinstance(rj, dict):
                marker = rj.get("_backfill_marker")
                if marker:
                    already_backfilled.add(marker)

        for summary in summaries:
            marker = f"{summary['protocol_key']}::{summary['short_run_id']}"
            if marker in already_backfilled:
                print(f"  skip (already backfilled): {marker}")
                continue

            started = summary["started_at"]
            completed = summary["completed_at"]
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            start_naive = started.replace(tzinfo=None) if started else now
            end_naive = completed.replace(tzinfo=None) if completed else now

            print(
                f"  {'[dry-run] would insert' if dry_run else 'insert'}: "
                f"{summary['protocol_key']} run={summary['short_run_id']} "
                f"agents={len(summary['agents'])} started={start_naive:%Y-%m-%d %H:%M}"
            )

            if dry_run:
                continue

            run = Run(
                id=uuid.uuid4(),
                tenant_slug="local-dev",
                protocol_key=summary["protocol_key"],
                question=summary["question"][:2000],
                agent_keys=summary["agents"],
                source="backfill",
                status="completed",
                result_json={
                    "_backfill_marker": marker,
                    "_backfill_source_file": summary["path"],
                    "_backfill_entry_count": len(summary["entries"]),
                    "blackboard_entries": summary["entries"][:50],  # Cap to avoid huge rows
                    "truncated": len(summary["entries"]) > 50,
                },
                result_summary=summary["result_summary"],
                total_cost_usd=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                langfuse_trace_id=None,
                error_message=None,
                started_at=start_naive,
                completed_at=end_naive,
                created_at=now,
            )
            session.add(run)

        if not dry_run:
            await session.commit()
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", nargs="?", default="smoke-tests")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dir_path = Path(args.dir).resolve()
    if not dir_path.is_dir():
        print(f"not a directory: {dir_path}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(backfill(dir_path, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
