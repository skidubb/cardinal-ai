"""
Shared Notion output logic for all event types.

Each event type maps to a Notion database. This module handles creating pages
with the correct properties for each event type.
"""

import logging
from datetime import datetime
from typing import Any

from csuite.config import get_settings
from csuite.events import EventResult
from csuite.tools.notion_api import notion_create_page

logger = logging.getLogger(__name__)

# Known Notion database IDs — set via env or discovered at runtime
NOTION_DB_IDS: dict[str, str | None] = {
    "strategy_meeting": None,  # Created on first use
    "sprint": "30414917-f9e4-810c-9045-000b3a1b9eab",  # Existing Sprints DB
    "board_meeting": None,
    "audit": None,
}


def _date_property(dt: datetime) -> dict[str, Any]:
    return {"date": {"start": dt.strftime("%Y-%m-%d")}}


def _select_property(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


def _number_property(value: float) -> dict[str, Any]:
    return {"number": value}


async def write_event_to_notion(
    result: EventResult,
    database_id: str | None = None,
    extra_properties: dict[str, Any] | None = None,
) -> str | None:
    """Write an EventResult to a Notion database page.

    Args:
        result: The event result to write.
        database_id: Notion database ID. Falls back to NOTION_DB_IDS lookup.
        extra_properties: Additional Notion properties to set.

    Returns:
        Notion page URL if successful, None otherwise.
    """
    settings = get_settings()
    api_key = settings.notion_api_key

    if not api_key:
        logger.warning("Notion API key not configured — skipping Notion write")
        return None

    db_id = database_id or NOTION_DB_IDS.get(result.event_type)
    if not db_id:
        logger.warning(
            f"No Notion database ID for event type '{result.event_type}' — skipping"
        )
        return None

    # Build properties common to all events
    properties: dict[str, Any] = {
        "Date": _date_property(result.created_at),
        "Cost": _number_property(round(result.total_cost, 2)),
    }

    if extra_properties:
        properties.update(extra_properties)

    # Build title from topic (truncate for readability)
    title = result.topic[:80] + ("..." if len(result.topic) > 80 else "")

    try:
        page = await notion_create_page(
            parent_id=db_id,
            title=title,
            content=result.markdown_output,
            properties=properties,
            api_key=api_key,
        )
        if "error" in page:
            logger.error(f"Notion write failed: {page['error']}")
            return None
        url = page.get("url")
        logger.info(f"Event written to Notion: {url}")
        return url
    except Exception:
        logger.exception("Failed to write event to Notion")
        return None
