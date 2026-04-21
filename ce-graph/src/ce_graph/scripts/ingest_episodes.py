"""Ingest a batch of pre-fetched episodes into the knowledge graph.

Designed to be called from the ``ce-graph-backfill`` Claude Code agent,
which fetches data via Notion / Granola MCP tools, writes a JSON batch
file, and invokes this script via Bash.

Input: a JSON file containing a list of episode dicts:

    [
      {
        "name": "notion :: meeting notes :: Acme Q1 kickoff",
        "body": "Long text content...",
        "source_type": "notion_page",
        "source_id": "abc-123",
        "timestamp": "2026-03-15T14:30:00Z"
      },
      ...
    ]

Usage:
    python -m ce_graph.scripts.ingest_episodes /tmp/batch.json
    python -m ce_graph.scripts.ingest_episodes /tmp/batch.json --dry-run

Each episode triggers an LLM extraction call (Haiku 4.5 by default).
Cost is roughly $0.001-0.005 per episode.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from ce_graph.graphiti_client import GraphClient
from ce_graph.tenancy import current_tenant

logger = logging.getLogger("ce_graph.ingest_episodes")


def _parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    s = value.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


async def ingest(batch_path: Path, dry_run: bool, tenant_slug: str | None = None) -> int:
    if not batch_path.exists():
        print(f"Batch file not found: {batch_path}", file=sys.stderr)
        return 1
    episodes = json.loads(batch_path.read_text())
    if not isinstance(episodes, list):
        print("Batch file must contain a JSON list of episode dicts", file=sys.stderr)
        return 1
    print(f"Found {len(episodes)} episodes in {batch_path.name}")

    if dry_run:
        for i, ep in enumerate(episodes[:5], 1):
            print(f"  [dry-run #{i}] {ep.get('name')[:80]}  ({len(ep.get('body', ''))} chars)")
        if len(episodes) > 5:
            print(f"  ... and {len(episodes) - 5} more")
        return 0

    resolved = tenant_slug or current_tenant()
    print(f"Ingesting to tenant: {resolved}")
    graph = await GraphClient.for_tenant(resolved)
    ok = 0
    fail = 0
    for i, ep in enumerate(episodes, 1):
        try:
            await graph.add_episode(
                name=ep["name"],
                body=ep["body"],
                source_type=ep.get("source_type", "manual_entry"),
                source_id=ep.get("source_id"),
                timestamp=_parse_ts(ep.get("timestamp")),
            )
            ok += 1
        except Exception as exc:
            logger.warning("episode %s failed: %s", ep.get("name"), exc)
            fail += 1
        if i % 10 == 0:
            print(f"  {i}/{len(episodes)} ingested (ok={ok} fail={fail})")
    await graph.close()
    print(f"Done. ok={ok} fail={fail}")
    return 0 if fail == 0 else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_file", help="Path to JSON file containing episodes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tenant", help="Tenant slug (default: $CE_TENANT or cardinal-element)")
    args = ap.parse_args()
    return asyncio.run(ingest(Path(args.batch_file), args.dry_run, tenant_slug=args.tenant))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
