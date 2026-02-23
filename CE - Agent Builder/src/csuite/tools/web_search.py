"""
Web Search and Fetch tools for C-Suite agents.

Provides web research capability via Brave Search API and direct URL fetching.
Free tier: 2K queries/mo, 1 req/sec.
"""

import html.parser
import logging
from typing import Any

import httpx

from csuite.tools.resilience import with_retry

logger = logging.getLogger(__name__)

# Maximum characters for fetched page content
MAX_PAGE_CONTENT = 10_000


class _HTMLTextExtractor(html.parser.HTMLParser):
    """Extract visible text from HTML, stripping tags."""

    SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._text.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._text)


def _extract_text_from_html(html_content: str) -> str:
    """Extract visible text from HTML content."""
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html_content)
    except Exception:
        # Fallback: crude tag stripping
        import re
        return re.sub(r"<[^>]+>", " ", html_content)
    return extractor.get_text()


@with_retry(api_name="brave_search")
async def brave_web_search(
    query: str,
    count: int = 5,
    country: str = "us",
    api_key: str | None = None,
) -> dict[str, Any]:
    """Search the web using Brave Search API.

    Args:
        query: Search query string.
        count: Number of results (1-20, default 5).
        country: Country code for results (default "us").
        api_key: Brave Search API key.

    Returns:
        {"results": [...], "query": "..."} or {"error": "..."}
    """
    if not api_key:
        return {"error": "Brave Search API key not configured. Set BRAVE_API_KEY in .env"}

    count = max(1, min(20, count))

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": count, "country": country},
            headers={
                "X-Subscription-Token": api_key,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()

    web_results = data.get("web", {}).get("results", [])
    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "description": r.get("description", ""),
        }
        for r in web_results
    ]

    return {"results": results, "query": query}


@with_retry(api_name="brave_search")
async def fetch_web_page(
    url: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch and extract text content from a web page.

    Args:
        url: URL to fetch.
        api_key: Not used currently but reserved for future proxy/API use.

    Returns:
        {"url": "...", "content": "...", "title": "..."} or {"error": "..."}
    """
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "CardinalElement-CSuite/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "html" in content_type:
        text = _extract_text_from_html(response.text)
    else:
        text = response.text

    # Extract title from HTML
    title = ""
    if "html" in content_type:
        import re
        match = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()

    # Truncate to stay within tool result limits
    if len(text) > MAX_PAGE_CONTENT:
        text = text[:MAX_PAGE_CONTENT] + f"\n[TRUNCATED — original length: {len(text)} chars]"

    return {"url": url, "content": text, "title": title}
