"""Shared pytest fixtures for ce-shared tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ce_shared.env import KEY_REGISTRY


@pytest.fixture()
def tmp_env_file(tmp_path: Path) -> Path:
    """Create a temporary .env with ANTHROPIC_API_KEY and a ce-shared/ sentinel."""
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-test-123\n")
    # Create sentinel directory so _find_dotenv recognises the root
    (tmp_path / "ce-shared").mkdir()
    return env_file


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all KEY_REGISTRY keys from os.environ for test isolation."""
    for key in KEY_REGISTRY:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def populated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set all required registry keys to dummy values."""
    for key, meta in KEY_REGISTRY.items():
        if meta.required:
            monkeypatch.setenv(key, f"test-{key}")
