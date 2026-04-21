"""Backfill the knowledge graph from Granola meeting transcripts.

Pulls every Granola meeting from the last 6 months by default and ingests
each transcript as a Graphiti episode. Granola transcripts are the richest
source of client/engagement context Cardinal Element has -- meetings,
discoveries, working sessions all flow through here.

Usage:
    python -m ce_graph.scripts.backfill_granola              # last 6 months
    python -m ce_graph.scripts.backfill_granola --since 2025-01-01
    python -m ce_graph.scripts.backfill_granola --dry-run

Notes:
    Granola has no public REST API as of April 2026. This script reads from
    the local Granola SQLite cache (chat.db / granola sqlite) which is the
    authoritative source on Scott's Mac. If/when Granola ships a remote API,
    swap _read_meetings() for an HTTP fetch.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ce_shared.env import find_and_load_dotenv

from ce_graph.graphiti_client import GraphClient

logger = logging.getLogger("ce_graph.backfill_granola")

# Default Granola data location on macOS.
DEFAULT_GRANOLA_DB = Path.home() / "Library/Application Support/Granola/granola.db"


def _read_meetings(db_path: Path, since: datetime) -> list[dict[str, Any]]:
    """Read meetings + transcripts from the local Granola SQLite cache.

    Schema is approximate -- adjust column names once you've inspected
    the actual cache (``sqlite3 ~/Library/Application\\ Support/Granola/granola.db``).
    """
    if not db_path.exists():
        raise SystemExit(f"Granola DB not found at {db_path}. Use --db PATH.")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT id, title, started_at, ended_at, transcript, summary, attendees
            FROM meetings
            WHERE started_at >= ?
            ORDER BY started_at DESC
            """,
            (since.isoformat(),),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


async def backfill(
    since: datetime,
    dry_run: bool,
    db_path: Path,
    limit: int | None,
    tenant_slug: str,
) -> int:
    find_and_load_dotenv()
    meetings = _read_meetings(db_path, since)
    print(f"Found {len(meetings)} meetings since {since.date()}")
    print(f"Tenant target: {tenant_slug}")

    if dry_run:
        for m in meetings[: limit or 20]:
            print(f"  [dry-run] {m.get('started_at')} :: {m.get('title')}")
        return 0

    graph = await GraphClient.for_tenant(tenant_slug)
    ingested = 0
    for m in meetings:
        if limit and ingested >= limit:
            break
        title = m.get("title") or "(untitled meeting)"
        transcript = m.get("transcript") or ""
        summary = m.get("summary") or ""
        attendees = m.get("attendees") or ""
        if not transcript.strip() and not summary.strip():
            continue

        started = m.get("started_at")
        ts = (
            datetime.fromisoformat(started)
            if started else datetime.now(timezone.utc)
        )
        body = (
            f"Granola meeting: {title}\n"
            f"Date: {ts.isoformat()}\n"
            f"Attendees: {attendees}\n\n"
            f"Summary:\n{summary}\n\n"
            f"Transcript:\n{transcript}"
        )
        await graph.add_episode(
            name=f"granola :: {title}",
            body=body,
            source_type="granola_transcript",
            source_id=str(m.get("id")),
            timestamp=ts,
        )
        ingested += 1
        if ingested % 10 == 0:
            print(f"  ingested {ingested}...")

    await graph.close()
    print(f"Done. Ingested {ingested} meetings.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tenant",
        required=True,
        help="REQUIRED tenant slug. No default -- prevents silent ingest into the wrong graph.",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--since", type=str, default=None,
        help="ISO date. Default: 6 months ago.",
    )
    ap.add_argument("--db", type=str, default=str(DEFAULT_GRANOLA_DB))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    since = (
        datetime.fromisoformat(args.since)
        if args.since
        else datetime.now(timezone.utc) - timedelta(days=180)
    )
    return asyncio.run(
        backfill(
            since=since,
            dry_run=args.dry_run,
            db_path=Path(args.db),
            limit=args.limit,
            tenant_slug=args.tenant,
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
