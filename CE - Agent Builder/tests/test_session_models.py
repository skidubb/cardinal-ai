"""Tests for session models and managers — uses DuckDB fixture."""

from csuite.session import (
    Session,
    SessionManager,
)


class TestSessionModel:
    def test_add_message(self):
        s = Session(agent_role="ceo")
        msg = s.add_message("user", "What is our strategy?")
        assert msg.role == "user"
        assert msg.content == "What is our strategy?"
        assert len(s.messages) == 1

    def test_get_conversation_history(self):
        s = Session(agent_role="cfo")
        s.add_message("user", "Q1")
        s.add_message("assistant", "A1")
        history = s.get_conversation_history()
        assert history == [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

    def test_to_summary_with_title(self):
        s = Session(agent_role="ceo", title="Strategy Review")
        summary = s.to_summary()
        assert "Strategy Review" in summary
        assert "CEO" in summary

    def test_to_summary_from_first_message(self):
        s = Session(agent_role="cto")
        s.add_message("user", "What tech stack should we use?")
        summary = s.to_summary()
        assert "What tech stack" in summary

    def test_to_summary_empty(self):
        s = Session(agent_role="cpo")
        summary = s.to_summary()
        assert "Empty session" in summary

    def test_parent_session_id_default_none(self):
        s = Session(agent_role="ceo")
        assert s.parent_session_id is None

    def test_metadata_stores_kwargs(self):
        s = Session(agent_role="ceo")
        msg = s.add_message("assistant", "response", model="opus", usage={"tokens": 100})
        assert msg.metadata["model"] == "opus"


class TestSessionManager:
    def test_create_and_load(self, duckdb_store):
        mgr = SessionManager()
        session = mgr.create_session("ceo", title="Test")
        loaded = mgr.load(session.id, "ceo")
        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.agent_role == "ceo"

    def test_save_with_messages(self, duckdb_store):
        mgr = SessionManager()
        session = mgr.create_session("cfo")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there")
        mgr.save(session)
        loaded = mgr.load(session.id, "cfo")
        assert loaded is not None
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"

    def test_list_sessions(self, duckdb_store):
        mgr = SessionManager()
        mgr.create_session("ceo", title="S1")
        mgr.create_session("ceo", title="S2")
        mgr.create_session("cfo", title="S3")
        ceo_sessions = mgr.list_sessions("ceo")
        assert len(ceo_sessions) == 2

    def test_delete(self, duckdb_store):
        mgr = SessionManager()
        session = mgr.create_session("cto")
        assert mgr.delete(session.id) is True
        assert mgr.load(session.id, "cto") is None

    def test_delete_nonexistent(self, duckdb_store):
        mgr = SessionManager()
        assert mgr.delete("nonexistent") is False

    def test_fork(self, duckdb_store):
        mgr = SessionManager()
        original = mgr.create_session("ceo")
        original.add_message("user", "Original Q")
        mgr.save(original)
        forked = mgr.fork(original.id, "Forked Session", "ceo")
        assert forked is not None
        assert forked.id != original.id
        assert forked.parent_session_id == original.id
        assert len(forked.messages) == 1
        assert forked.title == "Forked Session"

    def test_fork_nonexistent(self, duckdb_store):
        mgr = SessionManager()
        assert mgr.fork("nope", "title", "ceo") is None
