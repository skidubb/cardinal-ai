"""Tests for Pinecone knowledge base integration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from csuite.tools.pinecone_kb import (
    ALL_NAMESPACES,
    ROLE_NAMESPACE_MAP,
    handle_pinecone_search,
    search_knowledge,
)


@pytest.fixture
def mock_pinecone_index():
    """Create a mock Pinecone index that returns sample results."""
    mock_index = MagicMock()
    mock_index.search.return_value = {
        "result": {
            "hits": [
                {
                    "_id": "rec-1",
                    "_score": 0.95,
                    "fields": {
                        "text": "Revenue architecture framework overview",
                        "source_file": "rev-arch.pdf",
                        "source_folder": "revenue-architecture",
                    },
                },
                {
                    "_id": "rec-2",
                    "_score": 0.85,
                    "fields": {
                        "text": "Demand generation playbook",
                        "source_file": "demand-gen.pdf",
                        "source_folder": "demand-gen",
                    },
                },
            ]
        }
    }
    return mock_index


@pytest.mark.asyncio
async def test_search_returns_results(mock_pinecone_index):
    with patch("pinecone.Pinecone") as mock_pc_cls:
        mock_pc_cls.return_value.Index.return_value = mock_pinecone_index

        results = await search_knowledge(
            api_key="test-key",
            index_host="test-host",
            query="revenue architecture",
            role="ceo",
        )

        assert len(results) > 0
        assert results[0]["text"] == "Revenue architecture framework overview"
        assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_namespace_routing_per_role(mock_pinecone_index):
    with patch("pinecone.Pinecone") as mock_pc_cls:
        mock_pc_cls.return_value.Index.return_value = mock_pinecone_index

        await search_knowledge(
            api_key="test-key",
            index_host="test-host",
            query="test",
            role="cfo",
        )

        # Should search each CFO namespace
        call_namespaces = [
            call.kwargs["namespace"] for call in mock_pinecone_index.search.call_args_list
        ]
        assert set(call_namespaces) == set(ROLE_NAMESPACE_MAP["cfo"])


@pytest.mark.asyncio
async def test_explicit_namespace_override(mock_pinecone_index):
    with patch("pinecone.Pinecone") as mock_pc_cls:
        mock_pc_cls.return_value.Index.return_value = mock_pinecone_index

        await search_knowledge(
            api_key="test-key",
            index_host="test-host",
            query="test",
            role="ceo",
            namespace="meddic",
        )

        # Should only search the explicit namespace
        assert mock_pinecone_index.search.call_count == 1
        assert mock_pinecone_index.search.call_args.kwargs["namespace"] == "meddic"


@pytest.mark.asyncio
async def test_deduplication_across_namespaces(mock_pinecone_index):
    with patch("pinecone.Pinecone") as mock_pc_cls:
        mock_pc_cls.return_value.Index.return_value = mock_pinecone_index

        # With multiple namespaces returning same IDs, should deduplicate
        results = await search_knowledge(
            api_key="test-key",
            index_host="test-host",
            query="test",
            role="ceo",  # 5 namespaces
        )

        # Only 2 unique IDs even though searched 5 namespaces
        assert len(results) == 2


@pytest.mark.asyncio
async def test_handle_missing_api_key():
    settings = MagicMock()
    settings.pinecone_api_key = None
    settings.pinecone_index_host = None

    result = await handle_pinecone_search({"query": "test"}, settings)
    parsed = json.loads(result)
    assert "error" in parsed
    assert "not configured" in parsed["error"]


@pytest.mark.asyncio
async def test_handle_missing_query():
    settings = MagicMock()
    settings.pinecone_api_key = "key"
    settings.pinecone_index_host = "host"

    result = await handle_pinecone_search({}, settings)
    parsed = json.loads(result)
    assert "error" in parsed


def test_all_roles_have_namespaces():
    for role in ["ceo", "cfo", "cto", "cmo", "coo", "cpo"]:
        assert role in ROLE_NAMESPACE_MAP
        assert len(ROLE_NAMESPACE_MAP[role]) > 0
        for ns in ROLE_NAMESPACE_MAP[role]:
            assert ns in ALL_NAMESPACES
