"""Tests for Notion API tools."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from csuite.tools.notion_api import notion_create_page, notion_query_database, notion_search


@pytest.mark.asyncio
async def test_notion_search_missing_api_key():
    result = await notion_search("test", api_key=None)
    assert "error" in result
    assert "API key" in result["error"]


@pytest.mark.asyncio
async def test_notion_search_success():
    mock_response = httpx.Response(
        200,
        json={
            "results": [
                {
                    "id": "abc-123",
                    "object": "page",
                    "url": "https://notion.so/abc",
                    "properties": {
                        "Name": {"type": "title", "title": [{"plain_text": "Sprint Registry"}]}
                    },
                }
            ]
        },
        request=httpx.Request("POST", "https://api.notion.com/v1/search"),
    )

    with patch("csuite.tools.notion_api.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await notion_search("Sprint", api_key="test-token")

    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Sprint Registry"
    assert result["results"][0]["type"] == "page"


@pytest.mark.asyncio
async def test_notion_query_database_missing_key():
    result = await notion_query_database("db-id", api_key=None)
    assert "error" in result


@pytest.mark.asyncio
async def test_notion_query_database_success():
    mock_response = httpx.Response(
        200,
        json={
            "results": [
                {
                    "id": "row-1",
                    "properties": {
                        "Name": {"type": "title", "title": [{"plain_text": "CTO-D6"}]},
                        "Status": {"type": "select", "select": {"name": "In Progress"}},
                        "Score": {"type": "number", "number": 85},
                    },
                }
            ]
        },
        request=httpx.Request("POST", "https://api.notion.com/v1/databases/db-id/query"),
    )

    with patch("csuite.tools.notion_api.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await notion_query_database("db-id", api_key="test-token")

    assert len(result["results"]) == 1
    assert result["results"][0]["properties"]["Name"] == "CTO-D6"
    assert result["results"][0]["properties"]["Status"] == "In Progress"
    assert result["results"][0]["properties"]["Score"] == 85


@pytest.mark.asyncio
async def test_notion_create_page_missing_key():
    result = await notion_create_page("parent-id", "Test", api_key=None)
    assert "error" in result


@pytest.mark.asyncio
async def test_notion_create_page_success():
    mock_response = httpx.Response(
        200,
        json={"id": "new-page-id", "url": "https://notion.so/new-page"},
        request=httpx.Request("POST", "https://api.notion.com/v1/pages"),
    )

    with patch("csuite.tools.notion_api.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await notion_create_page(
            "parent-id", "New Page", content="## Hello\n\n- Item 1\n- Item 2", api_key="test-token",
        )

    assert result["id"] == "new-page-id"
    assert result["title"] == "New Page"


@pytest.mark.asyncio
async def test_notion_search_api_error():
    mock_response = httpx.Response(
        401,
        text="Unauthorized",
        request=httpx.Request("POST", "https://api.notion.com/v1/search"),
    )

    with patch("csuite.tools.notion_api.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await notion_search("test", api_key="bad-token")
