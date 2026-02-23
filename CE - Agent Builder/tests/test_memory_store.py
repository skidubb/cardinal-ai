"""Tests for memory store — Pinecone-backed with mocked client."""

from unittest.mock import MagicMock, patch

from csuite.memory.store import MemoryStore

_SETTINGS = "csuite.memory.store.get_settings"
_INDEX = "csuite.memory.store._get_index"


def _mock_settings(enabled: bool = True, configured: bool = True) -> MagicMock:
    s = MagicMock()
    s.memory_enabled = enabled
    s.pinecone_api_key = "pk-test" if configured else None
    s.pinecone_learning_index_host = "https://test-host" if configured else None
    return s


class TestMemoryStore:
    def test_store_returns_true_when_enabled(self):
        mock_index = MagicMock()
        with patch(_SETTINGS, return_value=_mock_settings()), \
             patch(_INDEX, return_value=mock_index):
            ms = MemoryStore()
            result = ms.store(
                role="ceo", content="Key decision made",
                memory_type="decision", session_id="s1", summary="Decision",
            )
            assert result is True
            mock_index.upsert_records.assert_called_once()

    def test_store_returns_false_when_disabled(self):
        with patch(_SETTINGS, return_value=_mock_settings(enabled=False)):
            ms = MemoryStore()
            result = ms.store(role="ceo", content="X", memory_type="decision")
            assert result is False

    def test_store_returns_false_when_not_configured(self):
        with patch(_SETTINGS, return_value=_mock_settings(configured=False)):
            ms = MemoryStore()
            assert ms.enabled is False
            result = ms.store(role="ceo", content="X", memory_type="decision")
            assert result is False

    def test_retrieve_returns_results(self):
        mock_index = MagicMock()
        mock_index.search.return_value = {
            "result": {
                "hits": [
                    {
                        "_id": "ceo-123",
                        "_score": 0.95,
                        "fields": {
                            "text": "Revenue grew 20%",
                            "summary": "Revenue growth",
                            "memory_type": "fact",
                            "timestamp": 1000,
                        },
                    }
                ]
            }
        }
        with patch(_SETTINGS, return_value=_mock_settings()), \
             patch(_INDEX, return_value=mock_index):
            ms = MemoryStore()
            results = ms.retrieve("cfo", "revenue growth", top_k=5)
            assert len(results) == 1
            assert results[0]["content"] == "Revenue grew 20%"
            assert results[0]["score"] == 0.95

    def test_retrieve_disabled_returns_empty(self):
        with patch(_SETTINGS, return_value=_mock_settings(enabled=False)):
            ms = MemoryStore()
            results = ms.retrieve("ceo", "anything")
            assert results == []

    def test_store_handles_exception_gracefully(self):
        mock_index = MagicMock()
        mock_index.upsert_records.side_effect = Exception("Pinecone error")
        with patch(_SETTINGS, return_value=_mock_settings()), \
             patch(_INDEX, return_value=mock_index):
            ms = MemoryStore()
            result = ms.store(role="ceo", content="X", memory_type="fact")
            assert result is False

    def test_retrieve_handles_exception_gracefully(self):
        mock_index = MagicMock()
        mock_index.search.side_effect = Exception("Pinecone error")
        with patch(_SETTINGS, return_value=_mock_settings()), \
             patch(_INDEX, return_value=mock_index):
            ms = MemoryStore()
            results = ms.retrieve("ceo", "query")
            assert results == []
