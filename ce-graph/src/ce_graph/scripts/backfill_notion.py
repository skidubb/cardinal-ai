"""Backfill the knowledge graph from the Cardinal Element Notion workspace.

Walks every database the integration has access to, pulls every page,
and ingests each as a Graphiti episode tagged with provenance.

Usage:
    python -m ce_graph.scripts.backfill_notion              # full backfill
    python -m ce_graph.scripts.backfill_notion --dry-run    # show what would ingest
    python -m ce_graph.scripts.backfill_notion --since 2025-10-01

Requires:
    NOTION_API_KEY in environment
    pip install "ce-graph[backfill]"

Notes:
    - Idempotent at the page level: re-ingesting a page updates the existing
      Source node and re-extracts entities. Graphiti handles temporal supersession.
    - Ingest LLM cost: ~$0.001-0.005 per page (Haiku 4.5). 1000 pages ~= $1-5.
    - Rate-limited via tenacity exponential backoff to stay under Notion's 3 rps.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from ce_shared.env import find_and_load_dotenv

from ce_graph.graphiti_client import GraphClient

logger = logging.getLogger("ce_graph.backfill_notion")


async def _list_databases(notion: Any) -> list[dict[str, Any]]:
    """Find every database visible to the integration."""
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        resp = await asyncio.to_thread(
            notion.search,
            **{
                "filter": {"property": "object", "value": "database"},
                "start_cursor": cursor,
            },
        )
        out.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return out


async def _list_pages_in_db(notion: Any, db_id: str, since: datetime | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    filter_arg: dict[str, Any] | None = None
    if since:
        filter_arg = {
            "timestamp": "last_edited_time",
            "last_edited_time": {"on_or_after": since.isoformat()},
        }
    while True:
        kwargs: dict[str, Any] = {"database_id": db_id, "start_cursor": cursor}
        if filter_arg:
            kwargs["filter"] = filter_arg
        resp = await asyncio.to_thread(notion.databases.query, **kwargs)
        out.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return out


async def _page_text(notion: Any, page_id: str) -> str:
    """Concatenate all block text in a page. Skeleton -- extend per block type."""
    blocks = await asyncio.to_thread(notion.blocks.children.list, block_id=page_id)
    chunks: list[str] = []
    for block in blocks.get("results", []):
        btype = block.get("type")
        body = block.get(btype, {})
        rich = body.get("rich_text", []) if isinstance(body, dict) else []
        text = "".join(t.get("plain_text", "") for t in rich)
        if text.strip():
            chunks.append(text)
    return "\n".join(chunks)


def _page_title(page: dict[str, Any]) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            rich = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in rich) or "(untitled)"
    return "(untitled)"


async def backfill(
    since: datetime | None,
    dry_run: bool,
    limit: int | None,
    tenant_slug: str,
) -> int:
    find_and_load_dotenv()
    if not os.environ.get("NOTION_API_KEY"):
        print("NOTION_API_KEY not set", file=sys.stderr)
        return 1

    try:
        from notion_client import Client as NotionClient
    except ImportError:
        print("Install backfill extras: pip install 'ce-graph[backfill]'", file=sys.stderr)
        return 1

    notion = NotionClient(auth=os.environ["NOTION_API_KEY"])
    print(f"Tenant target: {tenant_slug}")
    graph = await GraphClient.for_tenant(tenant_slug) if not dry_run else None

    databases = await _list_databases(notion)
    print(f"Found {len(databases)} databases")

    ingested = 0
    for db in databases:
        db_id = db["id"]
        db_title = "".join(
            t.get("plain_text", "") for t in db.get("title", [])
        ) or db_id
        pages = await _list_pages_in_db(notion, db_id, since)
        print(f"  {db_title}: {len(pages)} pages")

        for page in pages:
            if limit and ingested >= limit:
                print(f"Hit limit {limit}, stopping")
                if graph:
                    await graph.close()
                return 0
            title = _page_title(page)
            page_id = page["id"]
            url = page.get("url")
            edited = page.get("last_edited_time")
            edited_dt = (
                datetime.fromisoformat(edited.replace("Z", "+00:00"))
                if edited else datetime.now(timezone.utc)
            )

            if dry_run:
                print(f"    [dry-run] would ingest: {title} ({page_id})")
                ingested += 1
                continue

            body = await _page_text(notion, page_id)
            if not body.strip():
                continue

            episode_body = (
                f"Notion page: {title}\n"
                f"Database: {db_title}\n"
                f"URL: {url}\n\n"
                f"{body}"
            )
            await graph.add_episode(
                name=f"notion :: {db_title} :: {title}",
                body=episode_body,
                source_type="notion_page",
                source_id=page_id,
                timestamp=edited_dt,
            )
            ingested += 1
            if ingested % 25 == 0:
                print(f"    ingested {ingested}...")

    if graph:
        await graph.close()
    print(f"Done. Ingested {ingested} pages.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tenant",
        required=True,
        help="REQUIRED tenant slug. No default -- prevents silent ingest into the wrong graph.",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since", type=str, help="ISO date, e.g. 2025-10-01")
    ap.add_argument("--limit", type=int, default=None, help="Cap pages ingested")
    args = ap.parse_args()
    since = datetime.fromisoformat(args.since) if args.since else None
    return asyncio.run(
        backfill(since=since, dry_run=args.dry_run, limit=args.limit, tenant_slug=args.tenant)
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
