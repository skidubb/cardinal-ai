"""Tests for ce_shared.env_check diagnostic module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ce_shared.env_check import check_stale_envs, group_keys_by_project, redact


# ---------------------------------------------------------------------------
# redact()
# ---------------------------------------------------------------------------


class TestRedact:
    def test_short_value(self) -> None:
        """Values under 8 chars should be fully masked."""
        assert redact("abc") == "***"
        assert redact("1234567") == "***"

    def test_exactly_eight(self) -> None:
        assert redact("12345678") == "1234***5678"

    def test_normal_api_key(self) -> None:
        assert redact("sk-ant-abcdef123456") == "sk-a***3456"

    def test_empty(self) -> None:
        assert redact("") == "***"


# ---------------------------------------------------------------------------
# check_stale_envs()
# ---------------------------------------------------------------------------


class TestCheckStaleEnvs:
    def test_none_found(self, tmp_path: Path) -> None:
        """No stale .env files -> empty list."""
        assert check_stale_envs(tmp_path) == []

    def test_stale_found(self, tmp_path: Path) -> None:
        """Create a fake stale .env in CE - Agent Builder and detect it."""
        ab_dir = tmp_path / "CE - Agent Builder"
        ab_dir.mkdir()
        stale = ab_dir / ".env"
        stale.write_text("OLD_KEY=value\n")

        result = check_stale_envs(tmp_path)
        assert len(result) == 1
        assert "CE - Agent Builder" in result[0]

    def test_multiple_stale(self, tmp_path: Path) -> None:
        for name in ["CE - Agent Builder", "CE - Multi-Agent Orchestration"]:
            d = tmp_path / name
            d.mkdir()
            (d / ".env").write_text("X=1\n")

        result = check_stale_envs(tmp_path)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# group_keys_by_project()
# ---------------------------------------------------------------------------


class TestGroupKeysByProject:
    def test_has_expected_groups(self) -> None:
        groups = group_keys_by_project()
        assert "agent-builder" in groups
        assert "orchestration" in groups

    def test_docker_group(self) -> None:
        groups = group_keys_by_project()
        assert "docker" in groups
        docker_names = [m.name for m in groups["docker"]]
        assert "POSTGRES_DB" in docker_names
        assert "POSTGRES_USER" in docker_names

    def test_anthropic_key_in_multiple_groups(self) -> None:
        """ANTHROPIC_API_KEY should appear in agent-builder, orchestration, and evals."""
        groups = group_keys_by_project()
        for project in ["agent-builder", "orchestration", "evals"]:
            names = [m.name for m in groups[project]]
            assert "ANTHROPIC_API_KEY" in names, f"Missing from {project}"
