#!/usr/bin/env python3
"""Backfill the `runs` table from Blackboard audit logs.

One-shot script to reconstruct Run rows from `smoke-tests/p*_<run_id>.jsonl`
files that were written before `persist_run()` was healthy end-to-end.

Sets source='backfill' so they're distinguishable from live runs.
Skips any file whose run_id already has a row in `runs`.

By default ALSO writes matching rows to the legacy `run` (SQLModel) table
so the portal UI displays them. Pass ``--skip-legacy`` to disable.

Usage:
    cd "CE - Multi-Agent Orchestration" && source venv/bin/activate
    python scripts/backfill_runs_from_jsonl.py [--dry-run] [--skip-legacy] [DIR]

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

# Ensure the orchestration dir (one level up from scripts/) is on sys.path so
# `from api.database import engine` resolves when the script is invoked as
# `python scripts/backfill_runs_from_jsonl.py` (Python otherwise only adds
# scripts/ to sys.path, not the orchestration root).
_ORCH_ROOT = Path(__file__).resolve().parent.parent
if str(_ORCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_ORCH_ROOT))

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


def _write_legacy_row(summary: dict, now: datetime) -> bool:
    """Insert a row into the old SQLModel `run` table so the UI shows it.

    Idempotent: if a row with matching (protocol_key, started_at, type='backfill')
    exists, returns True without re-inserting. Returns False on failure.
    """
    import json as _json

    try:
        from sqlmodel import Session as _SQLSess
        from sqlmodel import select as _sqlm_select

        from api.database import engine as _legacy_engine
        from api.models import Run as _LegacyRun
    except Exception as e:
        print(f"  legacy import failed: {e}", file=sys.stderr)
        return False
    try:
        started_naive = summary["started_at"].replace(tzinfo=None) if summary["started_at"] else now
        completed_naive = summary["completed_at"].replace(tzinfo=None) if summary["completed_at"] else now
        with _SQLSess(_legacy_engine) as session:
            existing = session.exec(
                _sqlm_select(_LegacyRun).where(
                    _LegacyRun.protocol_key == summary["protocol_key"],
                    _LegacyRun.started_at == started_naive,
                    _LegacyRun.type == "backfill",
                )
            ).first()
            if existing is not None:
                return True

            legacy_run = _LegacyRun(
                type="backfill",
                protocol_key=summary["protocol_key"],
                question=summary["question"][:2000],
                tenant_slug="local-dev",
                status="completed",
                cost_usd=0.0,
                trace_id=None,
                error_message=None,
                started_at=started_naive,
                completed_at=completed_naive,
                judge_verdict_json="{}",
                context_mode=None,
                context_files_json="[]",
                agent_keys_json=_json.dumps(summary["agents"] or []),
                steps_json="[]",
            )
            session.add(legacy_run)
            session.commit()
        return True
    except Exception as e:
        print(f"  legacy write failed for {summary['short_run_id']}: {e}", file=sys.stderr)
        return False


async def backfill(dir_path: Path, dry_run: bool = False, skip_legacy: bool = False) -> None:
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
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            legacy_written = False
            if not skip_legacy and not dry_run:
                legacy_written = _write_legacy_row(summary, now)

            if marker in already_backfilled:
                print(
                    f"  skip (ce-db already backfilled): {marker}"
                    + (" — legacy row added for UI" if legacy_written else "")
                )
                continue

            started = summary["started_at"]
            completed = summary["completed_at"]
            start_naive = started.replace(tzinfo=None) if started else now
            end_naive = completed.replace(tzinfo=None) if completed else now

            print(
                f"  {'[dry-run] would insert' if dry_run else 'insert'}: "
                f"{summary['protocol_key']} run={summary['short_run_id']} "
                f"agents={len(summary['agents'])} started={start_naive:%Y-%m-%d %H:%M}"
                + (" (+legacy row)" if legacy_written else "")
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
    parser.add_argument(
        "--skip-legacy",
        action="store_true",
        help="Only write to the new `runs` (ce-db) table; skip the legacy `run` (UI) table.",
    )
    args = parser.parse_args()
    dir_path = Path(args.dir).resolve()
    if not dir_path.is_dir():
        print(f"not a directory: {dir_path}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(backfill(dir_path, dry_run=args.dry_run, skip_legacy=args.skip_legacy))


if __name__ == "__main__":
    main()
