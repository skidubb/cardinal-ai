"""Tests for web search and fetch tools."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from csuite.tools.web_search import brave_web_search, fetch_web_page


@pytest.mark.asyncio
async def test_brave_web_search_missing_api_key():
    result = await brave_web_search("test query", api_key=None)
    assert "error" in result
    assert "API key" in result["error"]


@pytest.mark.asyncio
async def test_brave_web_search_success():
    mock_response = httpx.Response(
        200,
        json={
            "web": {
                "results": [
                    {"title": "Result 1", "url": "https://example.com/1", "description": "Desc 1"},
                    {"title": "Result 2", "url": "https://example.com/2", "description": "Desc 2"},
                ]
            }
        },
        request=httpx.Request("GET", "https://api.search.brave.com/res/v1/web/search"),
    )

    with patch("csuite.tools.web_search.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await brave_web_search("AI consulting", api_key="test-key")

    assert result["query"] == "AI consulting"
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "Result 1"


@pytest.mark.asyncio
async def test_brave_web_search_empty_results():
    mock_response = httpx.Response(
        200,
        json={"web": {"results": []}},
        request=httpx.Request("GET", "https://api.search.brave.com/res/v1/web/search"),
    )

    with patch("csuite.tools.web_search.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await brave_web_search("nonexistent query", api_key="test-key")

    assert result["results"] == []


@pytest.mark.asyncio
async def test_brave_web_search_api_error():
    mock_response = httpx.Response(
        429,
        text="Rate limited",
        request=httpx.Request("GET", "https://api.search.brave.com/res/v1/web/search"),
    )

    with patch("csuite.tools.web_search.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await brave_web_search("test", api_key="test-key")


@pytest.mark.asyncio
async def test_fetch_web_page_success():
    html = "<html><head><title>Test Page</title></head><body><p>Hello world</p></body></html>"
    mock_response = httpx.Response(
        200,
        text=html,
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("csuite.tools.web_search.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await fetch_web_page("https://example.com")

    assert result["url"] == "https://example.com"
    assert result["title"] == "Test Page"
    assert "Hello world" in result["content"]


@pytest.mark.asyncio
async def test_fetch_web_page_html_stripping():
    html = "<html><head><title>T</title></head><body><script>var x=1;</script><p>Visible</p><style>.x{}</style></body></html>"
    mock_response = httpx.Response(
        200,
        text=html,
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("csuite.tools.web_search.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await fetch_web_page("https://example.com")

    assert "Visible" in result["content"]
    assert "var x=1" not in result["content"]


@pytest.mark.asyncio
async def test_fetch_web_page_timeout():
    with patch("csuite.tools.web_search.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.TimeoutException):
            await fetch_web_page("https://slow-site.com")
