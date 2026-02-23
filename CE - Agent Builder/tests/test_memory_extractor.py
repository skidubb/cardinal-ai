"""Tests for memory extractor — uses mock Anthropic client."""

import json

import pytest

pytestmark = pytest.mark.integration
from unittest.mock import MagicMock, patch

from csuite.memory.extractor import extract_memories
from tests.conftest import make_api_response


class TestExtractMemories:
    def test_returns_parsed_json(self):
        memories = [{"memory_type": "decision", "summary": "Focus B2B", "content": "We chose B2B"}]
        resp = make_api_response(text=json.dumps(memories))
        mock_client = MagicMock()
        mock_client.messages.create.return_value = resp

        with patch("anthropic.Anthropic", return_value=mock_client), \
             patch("csuite.config.get_settings") as mock_gs:
            mock_gs.return_value.memory_enabled = True
            mock_gs.return_value.anthropic_api_key = "test-key"
            result = extract_memories("Some agent response", "ceo")
            assert len(result) == 1
            assert result[0]["memory_type"] == "decision"

    def test_returns_empty_for_empty_json(self):
        resp = make_api_response(text="[]")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = resp

        with patch("anthropic.Anthropic", return_value=mock_client), \
             patch("csuite.config.get_settings") as mock_gs:
            mock_gs.return_value.memory_enabled = True
            mock_gs.return_value.anthropic_api_key = "test-key"
            result = extract_memories("Nothing notable", "cfo")
            assert result == []

    def test_returns_empty_for_invalid_json(self):
        resp = make_api_response(text="not valid json")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = resp

        with patch("anthropic.Anthropic", return_value=mock_client), \
             patch("csuite.config.get_settings") as mock_gs:
            mock_gs.return_value.memory_enabled = True
            mock_gs.return_value.anthropic_api_key = "test-key"
            result = extract_memories("Response", "cto")
            assert result == []

    def test_returns_empty_when_disabled(self):
        with patch("csuite.config.get_settings") as mock_gs:
            mock_gs.return_value.memory_enabled = False
            result = extract_memories("Response", "cmo")
            assert result == []

    def test_returns_empty_on_api_error(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API down")

        with patch("anthropic.Anthropic", return_value=mock_client), \
             patch("csuite.config.get_settings") as mock_gs:
            mock_gs.return_value.memory_enabled = True
            mock_gs.return_value.anthropic_api_key = "test-key"
            result = extract_memories("Response", "ceo")
            assert result == []

    def test_uses_haiku_model(self):
        resp = make_api_response(text="[]")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = resp

        with patch("anthropic.Anthropic", return_value=mock_client), \
             patch("csuite.config.get_settings") as mock_gs:
            mock_gs.return_value.memory_enabled = True
            mock_gs.return_value.anthropic_api_key = "test-key"
            extract_memories("Response", "ceo")
            call_kwargs = mock_client.messages.create.call_args
            assert "haiku" in call_kwargs.kwargs.get("model", call_kwargs[1].get("model", ""))
