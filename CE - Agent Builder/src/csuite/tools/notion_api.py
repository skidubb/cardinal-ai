"""
Notion API integration for C-Suite agents.

Provides search, database query, and page creation via the Notion API.
Requires a Notion integration token with appropriate permissions.
"""

import logging
from typing import Any

import httpx

from csuite.tools.resilience import with_retry

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _markdown_to_notion_blocks(content: str) -> list[dict[str, Any]]:
    """Convert simple markdown to Notion block format.

    Handles paragraphs, headings (## and ###), and bullet lists (- item).
    """
    blocks: list[dict[str, Any]] = []
    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                },
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                },
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                },
            })
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                },
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                },
            })

    return blocks


def _extract_title(page: dict[str, Any]) -> str:
    """Extract title from a Notion page/database result."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_parts)
    # Fallback for database results
    title_list = page.get("title", [])
    if isinstance(title_list, list):
        return "".join(t.get("plain_text", "") for t in title_list)
    return ""


@with_retry(api_name="notion")
async def notion_search(
    query: str,
    filter_type: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Search Notion workspace for pages and databases.

    Args:
        query: Search query string.
        filter_type: Optional filter — "page" or "database".
        api_key: Notion integration token.

    Returns:
        {"results": [...]} or {"error": "..."}
    """
    if not api_key:
        return {"error": "Notion API key not configured. Set NOTION_API_KEY in .env"}

    body: dict[str, Any] = {"query": query}
    if filter_type in ("page", "database"):
        body["filter"] = {"property": "object", "value": filter_type}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{NOTION_API_BASE}/search",
            headers=_notion_headers(api_key),
            json=body,
        )
        response.raise_for_status()
        data = response.json()

    results = [
        {
            "id": r.get("id", ""),
            "title": _extract_title(r),
            "url": r.get("url", ""),
            "type": r.get("object", ""),
        }
        for r in data.get("results", [])
    ]

    return {"results": results}


@with_retry(api_name="notion")
async def notion_query_database(
    database_id: str,
    filter: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Query a Notion database.

    Args:
        database_id: The database ID to query.
        filter: Optional Notion filter object.
        sorts: Optional list of sort objects.
        api_key: Notion integration token.

    Returns:
        {"results": [...]} or {"error": "..."}
    """
    if not api_key:
        return {"error": "Notion API key not configured. Set NOTION_API_KEY in .env"}

    body: dict[str, Any] = {}
    if filter:
        body["filter"] = filter
    if sorts:
        body["sorts"] = sorts

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{NOTION_API_BASE}/databases/{database_id}/query",
            headers=_notion_headers(api_key),
            json=body,
        )
        response.raise_for_status()
        data = response.json()

    results = []
    for r in data.get("results", []):
        entry: dict[str, Any] = {"id": r.get("id", "")}
        props = r.get("properties", {})
        flat_props: dict[str, Any] = {}
        for name, prop in props.items():
            ptype = prop.get("type", "")
            if ptype == "title":
                flat_props[name] = "".join(
                    t.get("plain_text", "") for t in prop.get("title", [])
                )
            elif ptype == "rich_text":
                flat_props[name] = "".join(
                    t.get("plain_text", "") for t in prop.get("rich_text", [])
                )
            elif ptype == "number":
                flat_props[name] = prop.get("number")
            elif ptype == "select":
                sel = prop.get("select")
                flat_props[name] = sel.get("name", "") if sel else None
            elif ptype == "multi_select":
                flat_props[name] = [s.get("name", "") for s in prop.get("multi_select", [])]
            elif ptype == "date":
                d = prop.get("date")
                flat_props[name] = d.get("start", "") if d else None
            elif ptype == "checkbox":
                flat_props[name] = prop.get("checkbox", False)
            elif ptype == "status":
                st = prop.get("status")
                flat_props[name] = st.get("name", "") if st else None
            else:
                flat_props[name] = f"[{ptype}]"
        entry["properties"] = flat_props
        results.append(entry)

    return {"results": results}


@with_retry(api_name="notion")
async def notion_create_page(
    parent_id: str,
    title: str,
    content: str | None = None,
    properties: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Create a new page in Notion.

    Args:
        parent_id: Database ID or page ID for the parent.
        title: Page title.
        content: Optional markdown content for the page body.
        properties: Optional additional database properties.
        api_key: Notion integration token.

    Returns:
        {"id": "...", "url": "...", "title": "..."} or {"error": "..."}
    """
    if not api_key:
        return {"error": "Notion API key not configured. Set NOTION_API_KEY in .env"}

    # Build page body — try as database child first (uses "database_id" parent)
    body: dict[str, Any] = {
        "parent": {"database_id": parent_id},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            },
        },
    }

    # Merge additional properties
    if properties:
        for key, value in properties.items():
            if key == "title":
                continue  # Already set above
            # Accept raw Notion property format or simple values
            if isinstance(value, dict) and any(
                k in value for k in ("rich_text", "number", "select", "date", "checkbox")
            ):
                body["properties"][key] = value
            elif isinstance(value, str):
                body["properties"][key] = {
                    "rich_text": [{"type": "text", "text": {"content": value}}]
                }
            elif isinstance(value, (int, float)):
                body["properties"][key] = {"number": value}
            elif isinstance(value, bool):
                body["properties"][key] = {"checkbox": value}

    # Add content blocks
    if content:
        body["children"] = _markdown_to_notion_blocks(content)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{NOTION_API_BASE}/pages",
            headers=_notion_headers(api_key),
            json=body,
        )

        # If database_id fails, retry with page_id parent
        if response.status_code == 400:
            body["parent"] = {"page_id": parent_id}
            response = await client.post(
                f"{NOTION_API_BASE}/pages",
                headers=_notion_headers(api_key),
                json=body,
            )

        response.raise_for_status()
        data = response.json()

    return {
        "id": data.get("id", ""),
        "url": data.get("url", ""),
        "title": title,
    }
