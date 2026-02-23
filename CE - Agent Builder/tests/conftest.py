"""Shared test fixtures for C-Suite test suite."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from csuite.storage.duckdb_store import DuckDBStore

# ---------------------------------------------------------------------------
# DuckDB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_duckdb_path(tmp_path: Path) -> Path:
    return tmp_path / "test.duckdb"


@pytest.fixture
def duckdb_store(temp_duckdb_path: Path) -> DuckDBStore:
    store = DuckDBStore(db_path=temp_duckdb_path)
    # Reset lazy-loaded globals in modules that cache the store
    import csuite.learning.experience_log as _exp_mod
    import csuite.learning.preferences as _pref_mod
    import csuite.session as _sess_mod

    old_stores = (
        _sess_mod._store, _exp_mod._store, _pref_mod._store,
    )
    _sess_mod._store = None
    _exp_mod._store = None
    _pref_mod._store = None

    yield store

    # Restore
    _sess_mod._store, _exp_mod._store, _pref_mod._store = old_stores
    store.close()


# ---------------------------------------------------------------------------
# Mock Anthropic API
# ---------------------------------------------------------------------------

def _make_usage(input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = 0
    return usage


def make_text_block(text: str = "Mock response") -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(
    tool_name: str = "test_tool",
    tool_input: dict | None = None,
    tool_id: str = "tu_123",
) -> MagicMock:
    block = MagicMock(spec=[])  # spec=[] prevents auto-creating attributes
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input or {}
    block.id = tool_id
    # Explicitly do NOT set block.text — hasattr(block, "text") should return False
    return block


def make_api_response(
    text: str = "Mock response",
    stop_reason: str = "end_turn",
    model: str = "claude-opus-4-6",
    input_tokens: int = 100,
    output_tokens: int = 50,
    content: list | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.model = model
    resp.stop_reason = stop_reason
    resp.usage = _make_usage(input_tokens, output_tokens)
    if content is not None:
        resp.content = content
    else:
        resp.content = [make_text_block(text)]
    return resp


@pytest.fixture
def mock_anthropic_response():
    """Factory fixture — call with kwargs to customise."""
    return make_api_response


@pytest.fixture
def mock_anthropic_client():
    """Patches anthropic.Anthropic globally and returns the mock client."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = make_api_response()
    with patch("anthropic.Anthropic", return_value=mock_client):
        yield mock_client


# ---------------------------------------------------------------------------
# Mock Settings
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_settings(tmp_path: Path):
    """Provides a Settings mock with temp paths and memory enabled."""
    settings = MagicMock()
    settings.anthropic_api_key = "test-key-123"
    settings.default_model = "claude-opus-4-6"
    settings.memory_enabled = True
    settings.tools_enabled = True
    settings.tool_cost_limit = 1.00
    settings.session_cost_limit = 5.00
    settings.duckdb_path = tmp_path / "test.duckdb"
    settings.project_root = tmp_path
    settings.session_dir = tmp_path / "sessions"
    settings.reports_dir = tmp_path / "reports"
    return settings
