"""Tests for ce_shared.env — loader, registry, and validation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ce_shared.env import (
    KEY_REGISTRY,
    KeyMeta,
    _find_dotenv,
    find_and_load_dotenv,
    validate_env,
)


# ---- 1. Parent traversal ----

def test_find_dotenv_traverses_parents(tmp_path: Path) -> None:
    """_find_dotenv should walk up from CWD to find .env with sentinel."""
    # Set up: root has .env + ce-shared/ sentinel
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text("ANTHROPIC_API_KEY=sk-test\n")
    (root / "ce-shared").mkdir()

    # Nested directory that is CWD
    nested = root / "projects" / "sub"
    nested.mkdir(parents=True)

    with patch("ce_shared.env.Path.cwd", return_value=nested):
        result = _find_dotenv()

    assert result is not None
    assert result == root / ".env"


# ---- 2. Loading vars ----

def test_find_and_load_dotenv_loads_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """find_and_load_dotenv should load vars from .env into os.environ."""
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text("ANTHROPIC_API_KEY=sk-loaded-test\n")
    (root / "ce-shared").mkdir()

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with patch("ce_shared.env.Path.cwd", return_value=root):
        path = find_and_load_dotenv()

    assert path == root / ".env"
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-loaded-test"

    # Cleanup
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


# ---- 3. override=False ----

def test_override_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Shell-exported vars should take precedence over .env file values."""
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text("ANTHROPIC_API_KEY=from-dotenv\n")
    (root / "ce-shared").mkdir()

    # Simulate shell export
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-shell")

    with patch("ce_shared.env.Path.cwd", return_value=root):
        find_and_load_dotenv()

    assert os.environ["ANTHROPIC_API_KEY"] == "from-shell"


# ---- 4. Missing required raises ----

def test_validate_missing_required_raises(
    clean_env: None,  # noqa: ARG001
) -> None:
    """Missing ANTHROPIC_API_KEY should raise EnvironmentError."""
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        validate_env()


# ---- 5. Missing optional warns ----

def test_validate_missing_optional_warns(
    populated_env: None,  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Missing optional keys should log warnings, not raise."""
    with caplog.at_level(logging.WARNING, logger="ce_shared.env"):
        warnings = validate_env()

    # There should be warnings for missing optional keys
    assert len(warnings) > 0
    # No exception was raised — that's the assertion


# ---- 6. Project filter ----

def test_validate_project_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """With project='agent-builder', only agent-builder keys are checked."""
    # Set all required keys
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    # Remove an agent-builder optional key to see it in warnings
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    # Remove an orchestration-only optional key
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    warnings = validate_env(project="agent-builder")

    # PINECONE_API_KEY should warn (it's in agent-builder required_by)
    pinecone_warned = any("PINECONE_API_KEY" in w for w in warnings)
    assert pinecone_warned

    # LANGFUSE_SECRET_KEY should NOT be in warnings (orchestration-only)
    langfuse_warned = any("LANGFUSE_SECRET_KEY" in w for w in warnings)
    assert not langfuse_warned


# ---- 7. Registry completeness ----

def test_key_registry_completeness() -> None:
    """ANTHROPIC_API_KEY must be in the registry and marked required."""
    assert "ANTHROPIC_API_KEY" in KEY_REGISTRY
    meta = KEY_REGISTRY["ANTHROPIC_API_KEY"]
    assert isinstance(meta, KeyMeta)
    assert meta.required is True
    assert "agent-builder" in meta.required_by
    assert "orchestration" in meta.required_by
    assert "evals" in meta.required_by
