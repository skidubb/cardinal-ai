"""Tests for DuckDB storage layer."""

from pathlib import Path

import pytest

from csuite.storage.duckdb_store import DuckDBStore


@pytest.fixture
def store(tmp_path: Path) -> DuckDBStore:
    return DuckDBStore(db_path=tmp_path / "test.duckdb")


class TestExperienceLogs:
    def test_add_and_get_lessons(self, store: DuckDBStore) -> None:
        store.add_lesson("ceo", "Never recommend Canva", "2026-02-11 10:00")
        store.add_lesson("ceo", "ICP is B2B operators", "2026-02-11 10:01")
        rows = store.get_lessons("ceo")
        assert len(rows) == 2

    def test_trim_to_50(self, store: DuckDBStore) -> None:
        for i in range(60):
            store.add_lesson("ceo", f"lesson {i}", f"2026-02-11 {i:02d}:00")
        rows = store.get_lessons("ceo")
        assert len(rows) == 50


class TestPreferences:
    def test_save_and_load(self, store: DuckDBStore) -> None:
        data = {"corrections": [{"detail": "no canva"}], "risk_tolerance": "moderate"}
        store.save_preferences("ceo", data)
        loaded = store.load_preferences("ceo")
        assert loaded is not None
        assert loaded["risk_tolerance"] == "moderate"

    def test_load_missing(self, store: DuckDBStore) -> None:
        assert store.load_preferences("ceo") is None


class TestSessions:
    def test_save_load_roundtrip(self, store: DuckDBStore) -> None:
        store.save_session(
            session_id="abc123",
            agent_role="ceo",
            title="Test session",
            parent_session_id=None,
            metadata={"key": "value"},
            created_at="2026-02-11T10:00:00",
            updated_at="2026-02-11T10:00:00",
            messages=[
                {"role": "user", "content": "hello", "timestamp": "2026-02-11T10:00:00"},
                {"role": "assistant", "content": "hi", "timestamp": "2026-02-11T10:00:01"},
            ],
        )
        loaded = store.load_session("abc123")
        assert loaded is not None
        assert loaded["title"] == "Test session"
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["content"] == "hello"

    def test_list_sessions(self, store: DuckDBStore) -> None:
        for i in range(3):
            store.save_session(
                session_id=f"s{i}",
                agent_role="ceo",
                title=f"Session {i}",
                parent_session_id=None,
                metadata={},
                created_at=f"2026-02-11T1{i}:00:00",
                updated_at=f"2026-02-11T1{i}:00:00",
                messages=[],
            )
        sessions = store.list_sessions(agent_role="ceo")
        assert len(sessions) == 3

    def test_delete_session(self, store: DuckDBStore) -> None:
        store.save_session("del1", "ceo", "Delete me", None, {}, "2026-02-11T10:00:00",
                           "2026-02-11T10:00:00", [])
        assert store.delete_session("del1")
        assert store.load_session("del1") is None

    def test_fork_via_save(self, store: DuckDBStore) -> None:
        store.save_session("orig", "ceo", "Original", None, {}, "2026-02-11T10:00:00",
                           "2026-02-11T10:00:00",
                           [{"role": "user", "content": "q", "timestamp": "2026-02-11T10:00:00"}])
        orig = store.load_session("orig")
        assert orig is not None
        store.save_session("fork1", "ceo", "Forked", "orig", {}, "2026-02-11T11:00:00",
                           "2026-02-11T11:00:00", orig["messages"])
        forked = store.load_session("fork1")
        assert forked is not None
        assert forked["parent_session_id"] == "orig"
        assert len(forked["messages"]) == 1


class TestDebates:
    def test_save_load_debate(self, store: DuckDBStore) -> None:
        debate = {
            "id": "d1",
            "question": "Should we pivot?",
            "agent_roles": ["ceo", "cfo"],
            "total_rounds": 3,
            "rounds": [],
            "synthesis": None,
            "status": "in_progress",
            "created_at": "2026-02-11T10:00:00",
            "updated_at": "2026-02-11T10:00:00",
        }
        store.save_debate(debate)
        loaded = store.load_debate("d1")
        assert loaded is not None
        assert loaded["question"] == "Should we pivot?"
        assert loaded["agent_roles"] == ["ceo", "cfo"]

    def test_delete_debate(self, store: DuckDBStore) -> None:
        store.save_debate({
            "id": "d2", "question": "q", "agent_roles": [], "total_rounds": 1,
            "rounds": [], "status": "in_progress",
            "created_at": "2026-02-11T10:00:00", "updated_at": "2026-02-11T10:00:00",
        })
        assert store.delete_debate("d2")
        assert store.load_debate("d2") is None
